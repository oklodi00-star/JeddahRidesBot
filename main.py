"""
🤖 بوت المشاوير الذكي المتكامل - النسخة المطورة
يجمع بين الذكاء الاصطناعي والميزات الاجتماعية المتقدمة
"""

import os
import re
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = "8881485708:AAFH_dJW08U-S5a25nfLePTbV3g1Odzjxrk"

GROUP_ID = -1001234567890
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

OWNER_ID = 952638746
ADMIN_USERNAME = "klodi500"
ADMIN_USERNAMES = ["klodi500"]
ADMIN_IDS = [952638746]

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides_v2.db"

DRIVER_BADGE = "𓆩🚘𓆪 كابتن"
CUSTOMER_BADGE = "𓆩👤𓆪 عميل"

ENGAGEMENT_INTERVAL = 45 * 60

# ============================================================
# 📋 قانون القروب
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه مباشرة.

3️⃣ 🚕 الكابتن يضغط زر «أنا جاهز» تحت الطلب.

4️⃣ 💰 السعر والتفاهم بالخاص.

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🧠 كلمات ذكية للتمييز
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "دوام", "مدرسة", "جامعة",
    "مشوار يومي", "توصيل يومي", "التزام", "مكان المنزل", "مكان الدوام",
    "لوكيشن", "عدد الايام", "عدد ايام الدوام", "اسبوعي", "أسبوعي",
    "عقد شهري", "اتفاق شهري", "مشوار شهري", "توصيل شهري"
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني",
    "ابغى مشوار", "ابي مشوار", "احتاج توصيل",
    "من يوصلني", "فيه كابتن", "اوصلني", "ودني",
    "عايز مشوار", "عايزة مشوار", "محتاج توصيل"
]

CAPTAIN_KEYWORDS = [
    'كابتن', 'سائق', 'كباتن', 'سواق', 'معايا عربية', 'عندي عربية',
    'أنا كابتن', 'انا كابتن', 'سواق خاص', 'كابتن خاص', 'متاح',
    'فاضي', 'جاهز', 'موجود', 'أقدر', 'اقدر', 'سيارتي', 'عربيتي'
]

CLIENT_KEYWORDS = [
    'عايز', 'محتاج', 'ابغى', 'أبغى', 'أريد', 'اريد', 'بدور على',
    'مشوار', 'توصيلة', 'اوصل', 'أوصلني', 'عايزة', 'محتاجة',
    'ممكن توصيل', 'ممكن مشوار', 'احتاج', 'أحتاج'
]

LOCATION_KEYWORDS = [
    "متواجد", "أنا في", "انا في", "موجود", "بالحي", "بحي",
    "الان في", "الحين في", "تواجد", "أنا بحي", "انا بحي",
    "موقعي", "مكاني", "متواجدة", "موجودة"
]

TIME_PATTERNS = [
    r'(\d{1,2})\s*(ص|صبا|صباحا|م|مساء|مساءا|ظهر|عصر|مغرب|عشاء)',
    r'(بكرة|غدا|غداً|بعد غد|الاسبوع|الأسبوع|الشهر|الجمعة|السبت|الاحد|الأحد|الاثنين|الإثنين|الثلاثاء|الأربعاء|الخميس)',
    r'(\d{1,2}):(\d{2})'
]

# ============================================================
# 🎭 رسائل مزحة للكابتن
# ============================================================

DRIVER_JOKE_MESSAGES = [
    "😂 كابتن يطلب مشوار!",
    "🛠️ شكله تعطلت سيارته اليوم!",
    "🚕 الكابتن صار راكب اليوم! 😂",
    "😅 شكلها جات على الكابتن!",
    "😂 أووه! الكابتن يبي مشوار!",
    "🤣 الكابتن تعطلت سيارته!",
]

DRIVER_JOKE_ENDINGS = [
    "🚕 طيب يا كابتن، نوصلك؟ 😂",
    "😂 يلا بينا نودي الكابتن!",
    "🛣️ الله يعينك يا كابتن!",
    "😂 تصدق الكابتن يطلب توصيلة؟",
    "🚕 خل ننقذ الكابتن! 😂",
]

GREETINGS = [
    (["السلام عليكم", "سلام عليكم"], ["وعليكم السلام 🌹🚘", "وعليكم السلام يا هلا 👋"]),
    (["هلا", "مرحبا", "اهلا"], ["هلا وغلا 🌹", "يا هلا والله 👋"]),
    (["صباح الخير"], ["صباح النور ☀️🌹"]),
    (["مساء الخير"], ["مساء النور 🌙🌹"]),
]

CHAT_RESPONSES = [
    (["كيفك", "كيف حالك"], ["بخير 🌹", "تمام 😊"]),
    (["وش تسوي"], ["أنتظر مشوارك 😎🚘"]),
    (["تحبني"], ["أحبك ❤️"]),
    (["نكت", "قول نكتة"], ["مرة كابتن نسى العميل وراح 😂"]),
    (["شسمك"], ["اسمي بوت المشاوير الذكي 😎"]),
    (["طفشان", "ملل"], ["اطلب مشوار وتروق 🚘"]),
    (["احبك", "حبيبي"], ["حبيبي أنت 🌹"]),
    (["كم السعر"], ["💰 السعر بالتفاهم 🤝"]),
    (["بوت", "يا بوت"], ["نعم أنا هنا 🤖"]),
    (["شكرا", "يعطيك العافية"], ["العفو 🌹", "تحت أمرك 😊"]),
    (["وداعا", "باي", "مع السلامة"], ["في أمان الله 🌹", "الله يحفظك 👋"]),
]

READY_MESSAGES = [
    "رافقتك السلامة يا كابتن 🚕🌹",
    "الله يوفقك 🤲🚘",
]

ENGAGEMENT_MESSAGES = [
    "🌅 <b>صباح الخير!</b>\n\nمن عنده مشوار؟ 🚕",
    "🚕 <b>الكباتن!</b>\n\nأعلنوا مواقعكم 📍",
]

BAD_WORDS = ["يا غبي", "يا حمار", "انقلع"]

# ============================================================
# 💾 قاعدة البيانات المتطورة
# ============================================================

class Database:
    def __init__(self):
        self.db_file = DB_FILE
        self.init_db()
    
    def connect(self):
        con = sqlite3.connect(self.db_file)
        con.row_factory = sqlite3.Row
        return con
    
    def init_db(self):
        with self.connect() as con:
            cur = con.cursor()
            
            # جدول المستخدمين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    role TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    rating REAL DEFAULT 5.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول المشاوير
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    customer_id INTEGER,
                    captain_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    price REAL,
                    trip_date TEXT,
                    trip_time TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول الكباتن المستعدين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ready_drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER,
                    driver_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trip_id, driver_id)
                )
            """)
            
            # جدول المشاوير الشهرية
            cur.execute("""
                CREATE TABLE IF NOT EXISTS monthly_trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captain_id INTEGER,
                    client_id INTEGER,
                    pickup_location TEXT,
                    dropoff_location TEXT,
                    days TEXT,
                    time TEXT,
                    start_date DATE,
                    end_date DATE,
                    price REAL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # جدول تقييمات المستخدمين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rated_user_id INTEGER,
                    rated_by_id INTEGER,
                    rating REAL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            con.commit()
    
    def save_user(self, user):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO users (user_id, name, username)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    username = excluded.username
            """, (user.id, user.full_name, user.username or ""))
            con.commit()
    
    def set_role(self, user_id, role):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
            con.commit()
    
    def get_role(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else ""
    
    def get_user_role(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    
    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"
    
    def get_user(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def update_user_phone(self, user_id, phone):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
            con.commit()
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal", trip_date=None, trip_time=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips 
                (message_id, customer_id, pickup, destination, trip_type, trip_date, trip_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type, trip_date, trip_time))
            con.commit()
            return cur.lastrowid
    
    def get_trip(self, trip_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_trip_by_message(self, message_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE message_id = ?", (message_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id) VALUES (?, ?)", (trip_id, driver_id))
            con.commit()
            return cur.rowcount > 0
    
    def is_driver_ready(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM ready_drivers WHERE trip_id = ? AND driver_id = ?", (trip_id, driver_id))
            return cur.fetchone() is not None
    
    def get_ready_drivers(self, trip_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT u.* FROM ready_drivers rd
                JOIN users u ON rd.driver_id = u.user_id
                WHERE rd.trip_id = ?
            """, (trip_id,))
            return [dict(row) for row in cur.fetchall()]
    
    def update_trip_status(self, trip_id, status, captain_id=None):
        with self.connect() as con:
            cur = con.cursor()
            if captain_id:
                cur.execute("UPDATE trips SET status = ?, captain_id = ? WHERE trip_id = ?", 
                           (status, captain_id, trip_id))
            else:
                cur.execute("UPDATE trips SET status = ? WHERE trip_id = ?", (status, trip_id))
            con.commit()
    
    def create_monthly_trip(self, captain_id, client_id, pickup, dropoff, days, time, start_date, end_date, price=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO monthly_trips 
                (captain_id, client_id, pickup_location, dropoff_location, days, time, start_date, end_date, price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (captain_id, client_id, pickup, dropoff, days, time, start_date, end_date, price))
            con.commit()
            return cur.lastrowid
    
    def get_user_trips(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT * FROM trips 
                WHERE customer_id = ? OR captain_id = ?
                ORDER BY created_at DESC
            """, (user_id, user_id))
            return [dict(row) for row in cur.fetchall()]
    
    def get_monthly_trips(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT * FROM monthly_trips 
                WHERE captain_id = ? OR client_id = ?
                ORDER BY created_at DESC
            """, (user_id, user_id))
            return [dict(row) for row in cur.fetchall()]
    
    def rate_user(self, rated_user_id, rated_by_id, rating, comment=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO ratings (rated_user_id, rated_by_id, rating, comment)
                VALUES (?, ?, ?, ?)
            """, (rated_user_id, rated_by_id, rating, comment))
            con.commit()
            
            # تحديث متوسط التقييم
            cur.execute("""
                SELECT AVG(rating) as avg_rating FROM ratings WHERE rated_user_id = ?
            """, (rated_user_id,))
            avg_rating = cur.fetchone()[0]
            
            cur.execute("UPDATE users SET rating = ? WHERE user_id = ?", (avg_rating, rated_user_id))
            con.commit()

# ============================================================
# 🧠 معالج اللغة الطبيعية
# ============================================================

class NLPProcessor:
    def __init__(self):
        self.monthly_words = MONTHLY_TRIP_WORDS
        self.normal_words = NORMAL_TRIP_WORDS
        self.captain_words = CAPTAIN_KEYWORDS
        self.client_words = CLIENT_KEYWORDS
        self.location_words = LOCATION_KEYWORDS
    
    def normalize_text(self, text):
        """تطبيع النص العربي"""
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي", "ء": ""
        }
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def html_escape(self, text):
        """تهريب النص للـ HTML"""
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def detect_trip_type(self, text):
        """كشف نوع المشوار"""
        normalized = self.normalize_text(text)
        
        # فحص الكلمات الشهرية أولاً
        for word in self.monthly_words:
            if self.normalize_text(word) in normalized:
                return "monthly"
        
        # فحص الكلمات العادية
        for word in self.normal_words:
            if self.normalize_text(word) in normalized:
                return "normal"
        
        # فحص النمط "من... إلى..."
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return "normal"
        
        return None
    
    def looks_like_trip(self, text):
        """هل النص يبدو كطلب مشوار؟"""
        if self.detect_trip_type(text):
            return True
        
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return True
        
        trip_indicators = [
            "مكان المنزل", "مكان الدوام", "لوكيشن", "السعر",
            "التزام", "مشوار", "توصيل", "عدد الايام", "دوام",
            "اوصلني", "يوصلني", "يوديني", "ودني"
        ]
        
        normalized = self.normalize_text(text)
        for word in trip_indicators:
            if self.normalize_text(word) in normalized:
                return True
        return False
    
    def extract_route(self, text):
        """استخراج المسار من النص"""
        # نمط "من X إلى Y"
        match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # نمط "مكان المنزل: X" و "مكان الدوام: Y"
        home_match = re.search(r"مكان المنزل\s*[:：]\s*(.+)", text, re.IGNORECASE)
        work_match = re.search(r"مكان الدوام\s*[:：]\s*(.+)", text, re.IGNORECASE)
        if home_match and work_match:
            return home_match.group(1).strip(), work_match.group(1).strip()
        
        return None, None
    
    def detect_location(self, text):
        """كشف الموقع من النص"""
        normalized = self.normalize_text(text)
        
        found_keyword = False
        for keyword in self.location_words:
            if self.normalize_text(keyword) in normalized:
                found_keyword = True
                break
        
        if not found_keyword:
            return None
        
        # إزالة الكلمات المفتاحية
        for keyword in self.location_words:
            normalized = normalized.replace(self.normalize_text(keyword), "")
        
        location = normalized.strip()
        location = re.sub(r'[،.؟!]', '', location).strip()
        
        if not location or len(location) < 2:
            return None
        
        return location
    
    def extract_date_time(self, text):
        """استخراج التاريخ والوقت"""
        result = {'date': None, 'time': None}
        
        # استخراج الوقت
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(ص|صبا|صباحا|م|مساء|مساءا|ظهر|عصر|مغرب|عشاء)?', text)
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(3) if time_match.group(3) else None
            
            if period and ('م' in period or 'مساء' in period or 'عصر' in period or 'مغرب' in period or 'عشاء' in period):
                if hour < 12:
                    hour += 12
            elif period and ('ص' in period or 'صبا' in period or 'صباحا' in period):
                if hour == 12:
                    hour = 0
            
            result['time'] = f"{hour:02d}:{time_match.group(2) if time_match.group(2) else '00'}"
        
        # استخراج التاريخ
        today = datetime.now(SAUDI_TZ)
        if 'بكرة' in text or 'غدا' in text or 'غداً' in text:
            result['date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'بعد غد' in text:
            result['date'] = (today + timedelta(days=2)).strftime('%Y-%m-%d')
        else:
            days_map = {
                'السبت': 5, 'الأحد': 6, 'الاحد': 6, 'الاثنين': 0, 'الإثنين': 0,
                'الثلاثاء': 1, 'الأربعاء': 2, 'الاربعاء': 2, 'الخميس': 3, 'الجمعة': 4
            }
            
            for day_name, day_num in days_map.items():
                if day_name in text:
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    result['date'] = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    break
        
        if not result['date'] and not result['time']:
            result['date'] = today.strftime('%Y-%m-%d')
        
        return result
    
    def identify_role(self, text):
        """تحديد دور المستخدم"""
        normalized = self.normalize_text(text)
        
        captain_score = sum(1 for word in self.captain_words if self.normalize_text(word) in normalized)
        client_score = sum(1 for word in self.client_words if self.normalize_text(word) in normalized)
        
        if captain_score > client_score:
            return 'driver'
        elif client_score > captain_score:
            return 'customer'
        return None
    
    def get_chat_response(self, text):
        """الحصول على رد ذكي للمحادثة"""
        normalized = self.normalize_text(text)
        for phrases, responses in CHAT_RESPONSES:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        return None
    
    def get_greeting(self, text):
        """الحصول على رد التحية"""
        normalized = self.normalize_text(text)
        for phrases, responses in GREETINGS:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        return None

# ============================================================
# 🤖 البوت الرئيسي المتكامل
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()
        self.nlp = NLPProcessor()
    
    def get_user_badge(self, user_id):
        """الحصول على شارة المستخدم"""
        role = self.db.get_role(user_id)
        if role == "driver":
            return DRIVER_BADGE
        elif role == "customer":
            return CUSTOMER_BADGE
        return "𓆩❓𓆪 عضو"
    
    def create_trip_keyboard(self, trip_id, is_driver=False):
        """إنشاء لوحة مفاتيح المشوار"""
        keyboard = []
        
        if is_driver:
            keyboard.append([
                InlineKeyboardButton("🚕 أنا جاهز", callback_data=f"ready_{trip_id}"),
                InlineKeyboardButton("❌ إلغاء", callback_data=f"cancel_ready_{trip_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🚕 أنا جاهز", callback_data=f"ready_{trip_id}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("📞 تواصل", callback_data=f"contact_{trip_id}"),
            InlineKeyboardButton("⭐ تقييم", callback_data=f"rate_{trip_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def create_main_menu(self, user_id):
        """إنشاء القائمة الرئيسية"""
        role = self.db.get_role(user_id)
        keyboard = []
        
        if role == "driver":
            keyboard.append([
                InlineKeyboardButton("🚗 المشاوير المتاحة", callback_data="available_trips"),
                InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
            ])
            keyboard.append([
                InlineKeyboardButton("📅 المشاوير الشهرية", callback_data="monthly_trips"),
                InlineKeyboardButton("👤 حسابي", callback_data="my_account")
            ])
        elif role == "customer":
            keyboard.append([
                InlineKeyboardButton("🔍 طلب مشوار", callback_data="request_trip"),
                InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
            ])
            keyboard.append([
                InlineKeyboardButton("📅 المشاوير الشهرية", callback_data="monthly_trips"),
                InlineKeyboardButton("👤 حسابي", callback_data="my_account")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("🚕 أنا كابتن", callback_data="register_driver"),
                InlineKeyboardButton("👤 أنا عميل", callback_data="register_customer")
            ])
        
        keyboard.append([
            InlineKeyboardButton("ℹ️ مساعدة", callback_data="help"),
            InlineKeyboardButton("📋 القوانين", callback_data="rules")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الرسائل الواردة"""
        if not update.message or not update.message.text:
            return
        
        user = update.effective_user
        text = update.message.text.strip()
        user_id = user.id
        
        # حفظ المستخدم
        self.db.save_user(user)
        
        # فحص الكلمات السيئة
        normalized = self.nlp.normalize_text(text)
        for bad_word in BAD_WORDS:
            if self.nlp.normalize_text(bad_word) in normalized:
                await update.message.reply_text(
                    "⚠️ <b>من فضلك التزم بالأدب في الكلام</b>",
                    parse_mode=ParseMode.HTML
                )
                return
        
        # الرد على التحية
        greeting = self.nlp.get_greeting(text)
        if greeting:
            await update.message.reply_text(greeting)
            return
        
        # الرد على المحادثة
        chat_response = self.nlp.get_chat_response(text)
        if chat_response:
            await update.message.reply_text(chat_response)
            return
        
        # كشف طلب المشوار
        if self.nlp.looks_like_trip(text):
            trip_type = self.nlp.detect_trip_type(text)
            pickup, destination = self.nlp.extract_route(text)
            date_time = self.nlp.extract_date_time(text)
            
            # كشف الدور
            role = self.nlp.identify_role(text)
            user_role = self.db.get_role(user_id)
            
            # إذا كان كابتن يطلب مشوار (مزحة)
            if user_role == "driver" and trip_type == "normal":
                joke = random.choice(DRIVER_JOKE_MESSAGES)
                ending = random.choice(DRIVER_JOKE_ENDINGS)
                await update.message.reply_text(f"{joke}\n{ending}")
                return
            
            # إنشاء المشوار
            trip_id = self.db.create_trip(
                message_id=update.message.message_id,
                customer_id=user_id,
                pickup=pickup or "غير محدد",
                destination=destination or "غير محدد",
                trip_type=trip_type or "normal",
                trip_date=date_time['date'],
                trip_time=date_time['time']
            )
            
            # إنشاء رد المشوار
            badge = self.get_user_badge(user_id)
            type_text = "🔄 شهري" if trip_type == "monthly" else "✨ عادي"
            
            trip_text = f"""
🚕 <b>مشوار جديد!</b>

{badge}: {self.nlp.html_escape(user.full_name)}

📋 <b>النوع:</b> {type_text}
📍 <b>من:</b> {self.nlp.html_escape(pickup or 'غير محدد')}
🎯 <b>إلى:</b> {self.nlp.html_escape(destination or 'غير محدد')}
📅 <b>التاريخ:</b> {date_time['date'] or 'اليوم'}
⏰ <b>الوقت:</b> {date_time['time'] or 'غير محدد'}

🚕 <b>الكباتن اضغطوا "أنا جاهز"</b>
"""
            
            keyboard = self.create_trip_keyboard(trip_id, is_driver=(user_role == "driver"))
            
            await update.message.reply_text(
                trip_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            return
        
        # كشف الموقع
        location = self.nlp.detect_location(text)
        if location:
            role = self.db.get_role(user_id)
            if role == "driver":
                badge = DRIVER_BADGE
                await update.message.reply_text(
                    f"{badge} <b>{self.nlp.html_escape(user.full_name)}</b>\n"
                    f"📍 <b>متواجد في:</b> {self.nlp.html_escape(location)}",
                    parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    f"📍 <b>تم تسجيل موقعك:</b> {self.nlp.html_escape(location)}",
                    parse_mode=ParseMode.HTML
                )
            return
        
        # رد افتراضي
        await update.message.reply_text(
            "🤖 <b>أنا بوت المشاوير الذكي!</b>\n\n"
            "يمكنني مساعدتك في:\n"
            "• طلب مشوار عادي أو شهري\n"
            "• الإعلان عن موقعك\n"
            "• الرد على استفساراتك\n\n"
            "<b>جرب أن تقول:</b>\n"
            "• «عايز مشوار من الحمراء للسلامة»\n"
            "• «محتاج كابتن لمشوار شهري للدوام»\n"
            "• «أنا كابتن متواجد في الروضة»",
            parse_mode=ParseMode.HTML,
            reply_markup=self.create_main_menu(user_id)
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأزرار التفاعلية"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        data = query.data
        
        # تسجيل كابتن
        if data == "register_driver":
            self.db.set_role(user_id, "driver")
            await query.edit_message_text(
                f"✅ <b>تم تسجيلك ككابتن بنجاح!</b>\n\n"
                f"{DRIVER_BADGE}\n\n"
                f"الآن يمكنك:\n"
                f"• الإعلان عن موقعك\n"
                f"• الضغط على «أنا جاهز» تحت المشاوير\n"
                f"• استقبال طلبات العملاء",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # تسجيل عميل
        elif data == "register_customer":
            self.db.set_role(user_id, "customer")
            await query.edit_message_text(
                f"✅ <b>تم تسجيلك كعميل بنجاح!</b>\n\n"
                f"{CUSTOMER_BADGE}\n\n"
                f"الآن يمكنك:\n"
                f"• طلب مشاوير عادية أو شهرية\n"
                f"• التواصل مع الكباتن\n"
                f"• تقييم الخدمة",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # الكابتن جاهز
        elif data.startswith("ready_"):
            trip_id = int(data.split("_")[1])
            trip = self.db.get_trip(trip_id)
            
            if trip:
                if self.db.add_ready_driver(trip_id, user_id):
                    driver_badge = self.get_user_badge(user_id)
                    
                    # إشعار العميل
                    customer_id = trip['customer_id']
                    try:
                        await context.bot.send_message(
                            customer_id,
                            f"🚕 <b>كابتن جاهز لمشوارك!</b>\n\n"
                            f"{driver_badge}: {self.nlp.html_escape(user.full_name)}\n"
                            f"📍 من: {self.nlp.html_escape(trip['pickup'])}\n"
                            f"🎯 إلى: {self.nlp.html_escape(trip['destination'])}\n\n"
                            f"<b>اضغط للتواصل معه</b>",
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(
                                    "📞 تواصل", 
                                    url=f"tg://user?id={user_id}"
                                )
                            ]])
                        )
                    except:
                        pass
                    
                    ready_msg = random.choice(READY_MESSAGES)
                    await query.edit_message_text(
                        f"{ready_msg}\n\n"
                        f"{driver_badge} <b>{self.nlp.html_escape(user.full_name)}</b>\n"
                        f"✅ <b>جاهز للمشوار!</b>",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.answer("⚠️ أنت جاهز بالفعل لهذا المشوار!", show_alert=True)
        
        # إلغاء الجاهزية
        elif data.startswith("cancel_ready_"):
            trip_id = int(data.split("_")[2])
            await query.edit_message_text(
                "❌ <b>تم إلغاء جاهزيتك</b>",
                parse_mode=ParseMode.HTML
            )
        
        # المشاوير المتاحة
        elif data == "available_trips":
            await query.edit_message_text(
                "🚗 <b>المشاوير المتاحة ستظهر هنا</b>\n\n"
                "تابع القروب للمشاوير الجديدة!",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # مشاويري
        elif data == "my_trips":
            trips = self.db.get_user_trips(user_id)
            if trips:
                trips_text = "📋 <b>مشاويرك:</b>\n\n"
                for trip in trips[:5]:
                    trips_text += f"🔹 مشوار #{trip['trip_id']}\n"
                    trips_text += f"📍 {trip['pickup']} → {trip['destination']}\n"
                    trips_text += f"📅 {trip['created_at']}\n\n"
                
                await query.edit_message_text(
                    trips_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_main_menu(user_id)
                )
            else:
                await query.edit_message_text(
                    "📭 <b>ليس لديك مشاوير بعد</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_main_menu(user_id)
                )
        
        # المشاوير الشهرية
        elif data == "monthly_trips":
            monthly_trips = self.db.get_monthly_trips(user_id)
            if monthly_trips:
                trips_text = "📅 <b>مشاويرك الشهرية:</b>\n\n"
                for trip in monthly_trips[:5]:
                    trips_text += f"🔸 #{trip['id']}\n"
                    trips_text += f"📍 {trip['pickup_location']} → {trip['dropoff_location']}\n"
                    trips_text += f"📅 الأيام: {trip['days']}\n\n"
                
                await query.edit_message_text(
                    trips_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_main_menu(user_id)
                )
            else:
                await query.edit_message_text(
                    "📅 <b>ليس لديك مشاوير شهرية</b>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_main_menu(user_id)
                )
        
        # حسابي
        elif data == "my_account":
            user_info = self.db.get_user(user_id)
            if user_info:
                role = "🚕 كابتن" if user_info['role'] == "driver" else "👤 عميل" if user_info['role'] == "customer" else "❓ غير محدد"
                
                account_text = f"""
👤 <b>معلومات حسابك</b>

<b>الاسم:</b> {self.nlp.html_escape(user_info['name'])}
<b>المعرف:</b> @{user_info['username'] if user_info['username'] else 'غير موجود'}
<b>الصفة:</b> {role}
<b>التقييم:</b> ⭐ {user_info['rating']}

<b>الإحصائيات:</b>
• المشاوير: {len(self.db.get_user_trips(user_id))}
• الشهرية: {len(self.db.get_monthly_trips(user_id))}
"""
                await query.edit_message_text(
                    account_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=self.create_main_menu(user_id)
                )
        
        # مساعدة
        elif data == "help":
            help_text = """
ℹ️ <b>مساعدة البوت الذكي</b>

<b>للكباتن:</b>
• سجل ككابتن من القائمة
• أعلن عن موقعك بقول «متواجد في...»
• اضغط «أنا جاهز» تحت المشاوير

<b>للعملاء:</b>
• سجل كعميل من القائمة
• اطلب مشوارك بذكر «من» و«إلى»
• حدد الوقت والتاريخ

<b>أنواع المشاوير:</b>
• عادي: مرة واحدة
• شهري: يتكرر يومياً/أسبوعياً

<b>أمثلة:</b>
• «عايز مشوار من الحمراء للسلامة بكرة 8»
• «محتاج كابتن شهري للدوام»
• «أنا كابتن متواجد في الروضة»
"""
            await query.edit_message_text(
                help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # القوانين
        elif data == "rules":
            await query.edit_message_text(
                RULES_TEXT,
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )

# ============================================================
# 🚀 تشغيل البوت
# ============================================================

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # إنشاء البوت
    bot = SmartRidesBot()
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", lambda u, c: bot.handle_message(u, c)))
    application.add_handler(CommandHandler("help", lambda u, c: bot.handle_message(u, c)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # تشغيل البوت
    print("🤖 البوت الذكي يعمل الآن...")
    print("اضغط Ctrl+C للإيقاف")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
