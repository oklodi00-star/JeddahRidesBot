"""
🤖 بوت المشاوير الذكي المتكامل - النسخة المطورة
بدون إشعارات خاصة + تذكر دور المستخدم نهائياً
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

TOKEN = os.environ.get("BOT_TOKEN", "8881485708:AAFH_dJW08U-S5a25nfLePTbV3g1Odzjxrk")

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

BAD_WORDS = ["يا غبي", "يا حمار", "انقلع"]

# ============================================================
# 💾 قاعدة البيانات
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
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ready_drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER,
                    driver_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trip_id, driver_id)
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
    
    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"
    
    def get_user(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
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
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي", "ء": ""
        }
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def html_escape(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def detect_trip_type(self, text):
        normalized = self.normalize_text(text)
        
        for word in self.monthly_words:
            if self.normalize_text(word) in normalized:
                return "monthly"
        
        for word in self.normal_words:
            if self.normalize_text(word) in normalized:
                return "normal"
        
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return "normal"
        
        return None
    
    def looks_like_trip(self, text):
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
        match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        home_match = re.search(r"مكان المنزل\s*[:：]\s*(.+)", text, re.IGNORECASE)
        work_match = re.search(r"مكان الدوام\s*[:：]\s*(.+)", text, re.IGNORECASE)
        if home_match and work_match:
            return home_match.group(1).strip(), work_match.group(1).strip()
        
        return None, None
    
    def detect_location(self, text):
        normalized = self.normalize_text(text)
        
        found_keyword = False
        for keyword in self.location_words:
            if self.normalize_text(keyword) in normalized:
                found_keyword = True
                break
        
        if not found_keyword:
            return None
        
        for keyword in self.location_words:
            normalized = normalized.replace(self.normalize_text(keyword), "")
        
        location = normalized.strip()
        location = re.sub(r'[،.؟!]', '', location).strip()
        
        if not location or len(location) < 2:
            return None
        
        return location
    
    def extract_date_time(self, text):
        result = {'date': None, 'time': None}
        
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
    
    def get_chat_response(self, text):
        normalized = self.normalize_text(text)
        for phrases, responses in CHAT_RESPONSES:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        return None
    
    def get_greeting(self, text):
        normalized = self.normalize_text(text)
        for phrases, responses in GREETINGS:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        return None

# ============================================================
# 🤖 البوت الرئيسي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()
        self.nlp = NLPProcessor()
    
    def get_user_badge(self, user_id):
        role = self.db.get_role(user_id)
        if role == "driver":
            return DRIVER_BADGE
        elif role == "customer":
            return CUSTOMER_BADGE
        return "𓆩❓𓆪 عضو"
    
    def create_trip_keyboard(self, trip_id):
        keyboard = [
            [InlineKeyboardButton("🚕 أنا جاهز", callback_data=f"ready_{trip_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_main_menu(self, user_id):
        role = self.db.get_role(user_id)
        keyboard = []
        
        if role == "driver":
            keyboard.append([
                InlineKeyboardButton("📍 الإعلان عن موقعي", callback_data="announce_location"),
                InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
            ])
        elif role == "customer":
            keyboard.append([
                InlineKeyboardButton("🔍 طلب مشوار", callback_data="request_trip"),
                InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
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
        if not update.message or not update.message.text:
            return
        
        user = update.effective_user
        text = update.message.text.strip()
        user_id = user.id
        
        # حفظ المستخدم
        self.db.save_user(user)
        
        # الحصول على دور المستخدم المحفوظ
        user_role = self.db.get_role(user_id)
        
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
            
            # إذا كان كابتن مسجل ويطلب مشوار (مزحة)
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
            
            keyboard = self.create_trip_keyboard(trip_id)
            
            await update.message.reply_text(
                trip_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            return
        
        # كشف الموقع
        location = self.nlp.detect_location(text)
        if location and user_role == "driver":
            badge = DRIVER_BADGE
            await update.message.reply_text(
                f"{badge} <b>{self.nlp.html_escape(user.full_name)}</b>\n"
                f"📍 <b>متواجد في:</b> {self.nlp.html_escape(location)}",
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
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        user_id = user.id
        data = query.data
        
        # تسجيل كابتن - مرة واحدة فقط
        if data == "register_driver":
            self.db.set_role(user_id, "driver")
            await query.edit_message_text(
                f"✅ <b>تم تسجيلك ككابتن نهائياً!</b>\n\n"
                f"{DRIVER_BADGE}\n\n"
                f"لن نسألك مرة أخرى عن صفتك.\n"
                f"الآن يمكنك:\n"
                f"• الإعلان عن موقعك\n"
                f"• الضغط على «أنا جاهز» تحت المشاوير",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # تسجيل عميل - مرة واحدة فقط
        elif data == "register_customer":
            self.db.set_role(user_id, "customer")
            await query.edit_message_text(
                f"✅ <b>تم تسجيلك كعميل نهائياً!</b>\n\n"
                f"{CUSTOMER_BADGE}\n\n"
                f"لن نسألك مرة أخرى عن صفتك.\n"
                f"الآن يمكنك:\n"
                f"• طلب مشاوير عادية أو شهرية",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # الكابتن جاهز - بدون إشعار خاص للعميل
        elif data.startswith("ready_"):
            trip_id = int(data.split("_")[1])
            trip = self.db.get_trip(trip_id)
            
            if trip:
                if self.db.add_ready_driver(trip_id, user_id):
                    badge = self.get_user_badge(user_id)
                    
                    # بدون إشعار خاص - فقط تحديث في نفس الرسالة
                    await query.edit_message_text(
                        f"✅ <b>{badge} {self.nlp.html_escape(user.full_name)} جاهز للمشوار!</b>\n\n"
                        f"📍 من: {self.nlp.html_escape(trip['pickup'])}\n"
                        f"🎯 إلى: {self.nlp.html_escape(trip['destination'])}",
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await query.answer("⚠️ أنت جاهز بالفعل لهذا المشوار!", show_alert=True)
        
        # الإعلان عن الموقع
        elif data == "announce_location":
            await query.edit_message_text(
                "📍 <b>اكتب موقعك الحالي:</b>\n\n"
                "مثال: «متواجد في الحمراء»",
                parse_mode=ParseMode.HTML
            )
        
        # مشاويري
        elif data == "my_trips":
            await query.edit_message_text(
                "📋 <b>مشاويرك ستظهر هنا</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=self.create_main_menu(user_id)
            )
        
        # مساعدة
        elif data == "help":
            help_text = """
ℹ️ <b>مساعدة البوت</b>

<b>للكباتن:</b>
• سجل مرة واحدة فقط
• أعلن عن موقعك
• اضغط «أنا جاهز» تحت المشاوير

<b>للعملاء:</b>
• سجل مرة واحدة فقط
• اطلب مشوارك بذكر «من» و«إلى»

<b>أمثلة:</b>
• «عايز مشوار من الحمراء للسلامة»
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
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    bot = SmartRidesBot()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", lambda u, c: bot.handle_message(u, c)))
    application.add_handler(CommandHandler("help", lambda u, c: bot.handle_message(u, c)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    print("🤖 البوت الذكي يعمل الآن...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
