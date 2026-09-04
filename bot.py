"""
🤖 بوت مشاوير جدة الذكي - النسخة النهائية المتكاملة
تدعم: فهم سياق متقدم، ذاكرة قصيرة، دعم المواقع والصور، توصيات ذكية، لوحة تحكم
"""

import os
import re
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Tuple, Dict, Any

# مكتبات تيليجرام
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    Location,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# محاولة استيراد spaCy (اختياري)
try:
    import spacy
    NLP_AVAILABLE = True
    try:
        nlp = spacy.load("ar_core_news_sm")
        NLP_MODEL_LOADED = True
    except:
        NLP_MODEL_LOADED = False
except ImportError:
    NLP_AVAILABLE = False
    NLP_MODEL_LOADED = False

# ============================================================
# ⚙️ الإعدادات العامة
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ضع معرف القروب الفعلي هنا
GROUP_ID = -1001234567890
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]  # أضف معرف المشرفين هنا

SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

# ============================================================
# 📋 القوانين
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب للمشاوير والنقل فقط.
2️⃣ العميل يكتب طلبه مباشرة.
3️⃣ 🚕 الكابتن يضغط زر «أنا جاهز للمشوار» تحت الطلب.
4️⃣ 💰 السعر والتفاهم بالخاص.
5️⃣ 🚫 يمنع الإعلان أو إرسال رسائل خارج موضوع المشاوير.
6️⃣ 🤝 الاحترام واجب بين الجميع.

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🧠 قوائم الكلمات والمفردات (موسّعة ومعرّبة)
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "يومياً", "دوام", "مدرسة",
    "جامعة", "مشوار يومي", "توصيل يومي", "التزام", "اسبوعي", "أسبوعي",
    "شهر", "شهرين", "راتب", "مداوم", "كل اسبوع", "كل أسبوع",
    "يومي", "اسبوعياً", "أسبوعياً", "شهرياً", "يومياً",
    "كل يومين", "اسبوعين", "أسبوعين", "مناوبات", "وردية"
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني", "ابغى مشوار",
    "ابي مشوار", "احتاج توصيل", "ابغا مشوار", "من يوصلني", "فيه كابتن",
    "اوصلني", "ودني", "خذني", "نبغى", "نبي", "ابي", "أبي", "ابغا",
    "أبغا", "اريد", "أريد", "عايز", "محتاج", "محتاجة",
    "أحتاج", "مين يوصل", "ابغى اروح", "ابي اروح", "اريد اروح",
    "أريد الذهاب", "أبغى أروح", "أبي أروح", "أحتاج أوصل",
    "محتاج أوصل", "عايز أوصل", "نبغى نروح", "نبي نروح",
    "من يقدر", "أحد يوصل", "أحد يودي", "أحد ياخذ", "أحد يركب",
    "دور لي", "لقيت لي", "توجد توصيلة"
]

PRESENCE_WORDS = [
    "متواجد", "موجود", "انا في", "أنا في", "انا عند", "أنا عند",
    "متوفر", "مستعد", "جاهز", "في الانتظار", "بالخدمة", "متواجده",
    "موجوده", "متواجدة", "موجودة", "واقف", "واقفه", "واقفة", "انتظر", "مستني",
    "في الموقع", "بالموقع", "متجهز", "متجهزة", "متاح", "متاحة",
    "أنا متواجد", "انا متواجد", "انا جاهز", "أنا جاهز", "موجودين",
    "متواجدين", "في الخدمة", "مستعدين", "جاهزين", "أنا بالخدمة",
    "انا بالخدمة", "أنا موجود", "انا موجود", "أنا واقف", "انا واقف"
]

# قائمة مواقع شاملة (يمكن توسيعها)
LOCATIONS = [
    "الفضيلة", "الرغامة", "جدة", "مكة", "الرياض", "الدمام", "المدينة",
    "الطائف", "أبها", "تبوك", "جازان", "الجنوب", "الشمال", "الشرق",
    "الغرب", "البلد", "البغدادية", "الروضة", "الصفا", "المروة", "النسيم",
    "السليمانية", "العزيزية", "الفيحاء", "الجامعة", "الحمراء", "الاندلس",
    "الأندلس", "الربوة", "النزهة", "المشرفة", "بني مالك", "الهدا",
    "الشفا", "الحمدانية", "السنابل", "المداين", "السالم",
    "حي", "شارع", "طريق", "بجانب", "قرب", "داخل",
    "المحمدية", "الزهراء", "الخالدية", "الصالحية", "النعيم", "الورود",
    "السلامة", "الشاطئ", "الابحر", "أبحر", "النور", "التوفيق",
    "العدل", "المنار", "الواحة", "الفيصلية", "الريان", "الوادي",
    "الفلاح", "النهضة", "الرابية", "الخزامى", "الياسمين", "الندى"
]

# ============================================================
# 💾 قاعدة البيانات
# ============================================================

class Database:
    def __init__(self):
        self.db_file = DB_FILE
        self.init_db()

    def connect(self):
        con = sqlite3.connect(self.db_file, timeout=30, check_same_thread=False)
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
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # جدول المشاوير
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    customer_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    original_text TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            # جدول السائقين المستعدين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ready_drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER,
                    driver_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trip_id, driver_id)
                )
            """)
            # جدول تواجد السائقين
            cur.execute("""
                CREATE TABLE IF NOT EXISTS driver_presence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER UNIQUE,
                    location TEXT,
                    latitude REAL,
                    longitude REAL,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # جدول آخر رسائل المستخدمين (للذاكرة القصيرة)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    user_id INTEGER,
                    message_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            # جدول الرسائل المكررة لمنع السبام
            cur.execute("""
                CREATE TABLE IF NOT EXISTS anti_spam (
                    user_id INTEGER,
                    message_text TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            con.commit()

    # -------- المستخدمون --------
    def save_user(self, user):
        if not user:
            return
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
            return row["role"] if row else ""

    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"

    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"

    def get_user_count(self):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM users")
            return cur.fetchone()["cnt"]

    # -------- المشاوير --------
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal", original_text=""):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips
                (message_id, customer_id, pickup, destination, trip_type, original_text)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type, original_text))
            con.commit()
            return cur.lastrowid

    def get_trip(self, trip_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_active_trips(self):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE status = 'active' ORDER BY created_at DESC")
            return [dict(row) for row in cur.fetchall()]

    def close_trip(self, trip_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("UPDATE trips SET status = 'closed' WHERE trip_id = ?", (trip_id,))
            con.commit()

    # -------- السائقون المستعدون --------
    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id)
                VALUES (?, ?)
            """, (trip_id, driver_id))
            con.commit()

    # -------- التواجد --------
    def set_presence(self, driver_id, location, latitude=None, longitude=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO driver_presence (driver_id, location, latitude, longitude)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(driver_id) DO UPDATE SET
                    location = excluded.location,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    last_update = CURRENT_TIMESTAMP
            """, (driver_id, location, latitude, longitude))
            con.commit()

    def get_presence(self, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM driver_presence WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_presences(self):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM driver_presence ORDER BY last_update DESC")
            return [dict(row) for row in cur.fetchall()]

    # -------- الذاكرة القصيرة --------
    def add_memory(self, user_id, text):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO user_memory (user_id, message_text) VALUES (?, ?)", (user_id, text))
            con.commit()
            # نحتفظ بآخر 5 رسائل فقط
            cur.execute("""
                DELETE FROM user_memory WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM user_memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5
                )
            """, (user_id, user_id))
            con.commit()

    def get_memory(self, user_id, limit=5):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT message_text FROM user_memory WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, limit))
            rows = cur.fetchall()
            return [row["message_text"] for row in rows]

    # -------- منع السبام --------
    def is_spam(self, user_id, text, within_seconds=60):
        now = datetime.now()
        cutoff = now - timedelta(seconds=within_seconds)
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT COUNT(*) as cnt FROM anti_spam
                WHERE user_id = ? AND message_text = ? AND timestamp > ?
            """, (user_id, text, cutoff.isoformat()))
            return cur.fetchone()["cnt"] > 0

    def add_spam_record(self, user_id, text):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("INSERT INTO anti_spam (user_id, message_text) VALUES (?, ?)", (user_id, text))
            con.commit()

    # -------- إحصائيات --------
    def get_stats(self):
        with self.connect() as con:
            cur = con.cursor()
            stats = {}
            cur.execute("SELECT COUNT(*) as cnt FROM users")
            stats['users'] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'driver'")
            stats['drivers'] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'")
            stats['customers'] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM trips")
            stats['trips'] = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) as cnt FROM trips WHERE status = 'active'")
            stats['active_trips'] = cur.fetchone()["cnt"]
            return stats

# ============================================================
# 🤖 البوت الذكي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()
        self.nlp = None
        if NLP_AVAILABLE and NLP_MODEL_LOADED:
            self.nlp = nlp

    # ---------- تحويل النص ----------
    def normalize_text(self, text):
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي", "ء": "", "ٱ": "ا", "ڪ": "ك",
            "ﮐ": "ك", "ڿ": "ك",
        }
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ---------- تحليل النوايا (تصنيف متقدم) ----------
    def classify_intent(self, text, user_role, previous_messages=None):
        """
        يُرجع تصنيف النية:
        - register_driver
        - register_customer
        - presence
        - trip
        - unknown
        """
        norm = self.normalize_text(text).strip()

        # تسجيل كابتن
        if norm in ["انا كابتن", "انا سايق", "انا سواق", "كابتن", "سايق", "سواق", "انا سائق"]:
            return "register_driver"
        # تسجيل عميل
        if norm in ["انا عميل", "انا زبون", "عميل", "زبون", "انا راكب"]:
            return "register_customer"

        # التواجد
        if self.detect_presence(text):
            if user_role == "driver":
                return "presence"
            else:
                return "presence_not_driver"  # يحتاج تسجيل

        # طلب مشوار
        if self.looks_like_trip(text):
            return "trip"

        # استخدام السياق السابق لتحسين الفهم
        if previous_messages:
            last_msg = previous_messages[0] if previous_messages else ""
            if self.looks_like_trip(last_msg):
                # إذا كانت الرسالة السابقة طلب مشوار والآن يحدد موقعاً
                if self.extract_location(text):
                    return "trip_detail"
            if self.detect_presence(last_msg):
                # إذا كانت السابقة تواجد والآن يحدد موقعاً
                if self.extract_location(text):
                    return "presence_detail"

        return "unknown"

    def detect_trip_type(self, text):
        normalized = self.normalize_text(text)
        for word in MONTHLY_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "monthly"
        for word in NORMAL_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "normal"
        if re.search(r"من\s+.+?\s+(?:الى|الي|لل|إلى)\s+.+", normalized, re.IGNORECASE):
            return "normal"
        return None

    def detect_presence(self, text):
        normalized = self.normalize_text(text)
        for word in PRESENCE_WORDS:
            if self.normalize_text(word) in normalized:
                return True
        return False

    def extract_location(self, text):
        # استخدام spaCy إذا كان متاحاً
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"]:
                    return ent.text

        # البحث في قائمة المواقع اليدوية
        normalized = self.normalize_text(text)
        for loc in LOCATIONS:
            if self.normalize_text(loc) in normalized:
                return loc

        # محاولة استخراج موقع بعد كلمات مثل "في" أو "عند"
        match = re.search(r"(?:في|عند|بـ|بالقرب من|قرب|داخل)\s+([\w\s]+)", normalized, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def looks_like_trip(self, text):
        normalized = self.normalize_text(text)

        # استبعاد التواجد
        if self.detect_presence(text):
            return False

        if self.detect_trip_type(text):
            return True

        # أنماط إضافية
        patterns = [
            r"من\s+.+?\s+(?:الى|الي|لل|إلى)\s+.+",
            r"اوصلني\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"يوديني\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"ابغى\s+اوصل\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"اريد\s+اوصل\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"احتاج\s+توصيل\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"ابي\s+اوصل\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"أبي\s+أروح\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            r"أبغى\s+أروح\s+من\s+.+?\s+(?:الى|الي|لل)\s+.+",
        ]
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True

        # إذا ذكر مكانين أو أكثر قد يكون طلب
        locations_found = [loc for loc in LOCATIONS if self.normalize_text(loc) in normalized]
        if len(locations_found) >= 2:
            return True

        return False

    def extract_route(self, text):
        normalized = self.normalize_text(text)
        # محاولة استخراج من وإلى
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي|لل|إلى)\s+(.+)", normalized, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # إذا لم يوجد نمط صريح، حاول استخراج موقعين من القائمة
        locations = [loc for loc in LOCATIONS if self.normalize_text(loc) in normalized]
        if len(locations) >= 2:
            return locations[0], locations[1]

        # استخدم spaCy لاستخراج الأماكن
        if self.nlp:
            doc = self.nlp(text)
            places = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]]
            if len(places) >= 2:
                return places[0], places[1]

        return None, None

    def extract_price(self, text):
        match = re.search(r"(?:السعر|سعر|المبلغ|بـ|ب)\s*[:：]?\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_maps_links(self, text):
        return re.findall(r"https?://(?:www\.)?(?:google\.[^/\s]+|maps\.google\.[^/\s]+)[^\s<>]+", text, re.IGNORECASE)

    # ---------- نظام التوصية الذكية ----------
    def recommend_drivers(self, pickup_location):
        """
        يبحث عن سائقين متواجدين قريبين من موقع الانطلاق (نصياً)
        """
        presences = self.db.get_all_presences()
        recommended = []
        pickup_norm = self.normalize_text(pickup_location)
        for presence in presences:
            loc = presence.get("location", "")
            loc_norm = self.normalize_text(loc)
            # تطابق بسيط: إذا تطابق الموقع أو جزء منه
            if pickup_norm and (pickup_norm in loc_norm or loc_norm in pickup_norm):
                recommended.append(presence["driver_id"])
        return recommended

    # ---------- معالجة الرسائل ----------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        if not message or not user:
            return

        self.db.save_user(user)
        text = message.text or message.caption or ""
        # إذا كانت الرسالة مشاركة موقع (Location)
        location_data = None
        if message.location:
            location_data = message.location
            # تحويل إلى نص تقريبي
            text = f"موقعي {location_data.latitude}, {location_data.longitude}"

        if not text:
            return

        # منع السبام (نفس الرسالة خلال دقيقة)
        if self.db.is_spam(user.id, text):
            return
        self.db.add_spam_record(user.id, text)

        # حفظ الرسالة في الذاكرة القصيرة
        self.db.add_memory(user.id, text)

        # الحالة الحالية للمستخدم في السياق
        state = context.user_data.get("state")

        # ============ معالجة الحالة ============
        if state == "awaiting_location":
            # نتوقع أن النص هو موقع الكابتن
            location = self.extract_location(text)
            if location_data:
                location = f"{location_data.latitude:.4f}, {location_data.longitude:.4f}"
            elif not location:
                location = text.strip()
            self.db.set_presence(user.id, location, 
                                 latitude=location_data.latitude if location_data else None,
                                 longitude=location_data.longitude if location_data else None)
            now = datetime.now(SAUDI_TZ)
            card = f"""
📍 <b>تم تسجيل تواجدك بنجاح!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(user.full_name)}
🚕 <b>الموقع:</b> {self.html(location)}
🕐 <b>الوقت:</b> {now.strftime('%H:%M')}

🙏 <b>الله يرزقك المشوار الطيب!</b>
"""
            await message.reply_text(card, parse_mode=ParseMode.HTML)
            context.user_data.pop("state", None)
            return

        if state == "awaiting_clarification":
            choice = text.strip()
            if choice in ["1", "طلب مشوار"]:
                context.user_data.pop("state", None)
                original_text = context.user_data.get("pending_text", text)
                await self.handle_trip_request(update, context, original_text)
                return
            elif choice in ["2", "إعلان تواجد"]:
                context.user_data.pop("state", None)
                role = self.db.get_role(user.id)
                if role == "driver":
                    location = self.extract_location(text)
                    if location_data:
                        location = f"{location_data.latitude:.4f}, {location_data.longitude:.4f}"
                    elif not location:
                        location = "غير محدد"
                    self.db.set_presence(user.id, location)
                    await message.reply_text("✅ تم تسجيل تواجدك.", parse_mode=ParseMode.HTML)
                else:
                    await message.reply_text("يجب التسجيل ككابتن أولاً.", parse_mode=ParseMode.HTML)
                return
            elif choice in ["3", "تسجيل"]:
                context.user_data.pop("state", None)
                await message.reply_text(
                    "اختر نوع التسجيل:\n1️⃣ كابتن\n2️⃣ عميل",
                    parse_mode=ParseMode.HTML
                )
                context.user_data["state"] = "awaiting_registration_choice"
                return
            else:
                await message.reply_text("لم أفهم اختيارك، حاول مرة أخرى.")
                return

        if state == "awaiting_registration_choice":
            choice = text.strip()
            if choice in ["1", "كابتن"]:
                self.db.set_role(user.id, "driver")
                context.user_data.pop("state", None)
                await message.reply_text(
                    "✅ تم تسجيلك ككابتن!\n📍 أرسل موقعك الحالي.",
                    parse_mode=ParseMode.HTML
                )
                context.user_data["state"] = "awaiting_location"
                return
            elif choice in ["2", "عميل"]:
                self.db.set_role(user.id, "customer")
                context.user_data.pop("state", None)
                await message.reply_text(
                    "✅ تم تسجيلك كعميل!\nالآن اكتب مشوارك مباشرة.",
                    parse_mode=ParseMode.HTML
                )
                return
            else:
                await message.reply_text("اختيار غير صحيح، اختر 1 أو 2.")
                return

        # ============ معالجة النية ============
        role = self.db.get_role(user.id)
        previous_messages = self.db.get_memory(user.id, limit=3)  # آخر 3 رسائل
        intent = self.classify_intent(text, role, previous_messages)

        if intent == "register_driver":
            if role == "driver":
                await message.reply_text(
                    "أنت مسجل ككابتن بالفعل ✅\nأرسل موقعك الحالي مباشرة.",
                    parse_mode=ParseMode.HTML
                )
                context.user_data["state"] = "awaiting_location"
            else:
                self.db.set_role(user.id, "driver")
                await message.reply_text(
                    "✅ تم تسجيلك ككابتن بنجاح!\n\n"
                    "📍 أعلن موقعك مثل:\nأنا متواجد في الحمدانية\n"
                    "أو أرسل موقعك الحالي من تيليجرام.",
                    parse_mode=ParseMode.HTML
                )
                context.user_data["state"] = "awaiting_location"
            return

        if intent == "register_customer":
            if role == "customer":
                await message.reply_text(
                    "أنت مسجل كعميل بالفعل ✅\nاكتب مشوارك.",
                    parse_mode=ParseMode.HTML
                )
            else:
                self.db.set_role(user.id, "customer")
                await message.reply_text(
                    "✅ تم تسجيلك كعميل بنجاح!\n\n"
                    "الآن اكتب مشوارك مباشرة 🚗\nمثال: من الفضيلة إلى الرغامة",
                    parse_mode=ParseMode.HTML
                )
            return

        if intent == "presence":
            # كابتن مسجل يعلن تواجده
            location = self.extract_location(text)
            if location_data:
                location = f"{location_data.latitude:.4f}, {location_data.longitude:.4f}"
            elif not location:
                location = "غير محدد"
            self.db.set_presence(user.id, location, 
                                 latitude=location_data.latitude if location_data else None,
                                 longitude=location_data.longitude if location_data else None)
            now = datetime.now(SAUDI_TZ)
            card = f"""
📍 <b>تم تسجيل تواجدك بنجاح!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(user.full_name)}
🚕 <b>الموقع:</b> {self.html(location)}
🕐 <b>الوقت:</b> {now.strftime('%H:%M')}

🙏 <b>الله يرزقك المشوار الطيب!</b>
"""
            await message.reply_text(card, parse_mode=ParseMode.HTML)
            return

        if intent == "presence_not_driver":
            await message.reply_text(
                "📝 <b>سجل نوعك أولاً لكي تتمكن من إعلان التواجد!</b>\n\n"
                "🚕 للكابتن: اكتب «أنا كابتن»\n👤 للعميل: اكتب «أنا عميل»",
                parse_mode=ParseMode.HTML
            )
            return

        if intent == "trip":
            await self.handle_trip_request(update, context, text)
            return

        if intent == "trip_detail":
            # استكمال تفاصيل رحلة من رسالة سابقة
            last_trip_text = previous_messages[0] if previous_messages else ""
            pickup, destination = self.extract_route(last_trip_text)
            if not pickup and not destination:
                # نحتاج إلى سؤال
                await message.reply_text("من فضلك اكتب الرحلة كاملة: من [الموقع] إلى [الوجهة]")
                return
            # استخدم التفاصيل الجديدة
            new_location = self.extract_location(text) or text.strip()
            if not pickup:
                pickup = new_location
            elif not destination:
                destination = new_location
            # إنشاء الرحلة
            trip_type = self.detect_trip_type(last_trip_text) or "normal"
            price = self.extract_price(last_trip_text)
            maps_links = self.extract_maps_links(last_trip_text)
            trip_id = self.db.create_trip(
                message_id=message.message_id,
                customer_id=user.id,
                pickup=pickup,
                destination=destination,
                trip_type=trip_type,
                original_text=last_trip_text
            )
            await self.show_trip_card(update, context, trip_id, pickup, destination, trip_type, price, maps_links, last_trip_text)
            return

        if intent == "presence_detail":
            # استكمال تواجد
            location = self.extract_location(text)
            if location_data:
                location = f"{location_data.latitude:.4f}, {location_data.longitude:.4f}"
            if location:
                self.db.set_presence(user.id, location)
                await message.reply_text(f"✅ تم تسجيل تواجدك في {self.html(location)}", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text("لم أستطع تحديد الموقع، أعد المحاولة.")
            return

        # نية غير معروفة
        await self.handle_unknown(update, context, text)

    async def handle_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        message = update.message
        user = update.effective_user

        # حفظ النص الأصلي في حالة اختيار "طلب مشوار"
        context.user_data["pending_text"] = text
        context.user_data["state"] = "awaiting_clarification"

        await message.reply_text(
            "❓ لم أفهم طلبك تماماً.\n"
            "هل تقصد:\n"
            "1️⃣ طلب مشوار\n"
            "2️⃣ إعلان تواجدك ككابتن\n"
            "3️⃣ التسجيل كعميل/كابتن\n\n"
            "اكتب الرقم أو أعد الصياغة.",
            parse_mode=ParseMode.HTML
        )

    async def handle_trip_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        message = update.message
        user = update.effective_user

        pickup, destination = self.extract_route(text)

        # إذا لم يتم استخراج نقطة الانطلاق أو الوجهة، اطلب منهما
        if not pickup or not destination:
            if not pickup and not destination:
                await message.reply_text(
                    "من فضلك حدد نقطة الانطلاق والوجهة.\n"
                    "مثال: من الحمدانية إلى البلد",
                    parse_mode=ParseMode.HTML
                )
            elif not pickup:
                await message.reply_text(
                    "من أين ستنطلق؟\n"
                    "اكتب: من [الموقع] إلى [الوجهة]",
                    parse_mode=ParseMode.HTML
                )
            else:
                await message.reply_text(
                    "إلى أين تريد الذهاب؟\n"
                    "اكتب: من [الموقع] إلى [الوجهة]",
                    parse_mode=ParseMode.HTML
                )
            # حفظ الحالة لطلب التفاصيل لاحقاً
            context.user_data["state"] = "awaiting_trip_details"
            context.user_data["pending_trip_text"] = text
            return

        trip_type = self.detect_trip_type(text) or "normal"
        price = self.extract_price(text)
        maps_links = self.extract_maps_links(text)

        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            original_text=text
        )

        await self.show_trip_card(update, context, trip_id, pickup, destination, trip_type, price, maps_links, text)

        # إرسال إشعار للسائقين الموصى بهم
        recommended_drivers = self.recommend_drivers(pickup)
        if recommended_drivers:
            for driver_id in recommended_drivers:
                try:
                    await context.bot.send_message(
                        chat_id=driver_id,
                        text=f"🚗 <b>يوجد مشوار جديد قريب من موقعك!</b>\n\n"
                             f"📍 من: {self.html(pickup)}\n"
                             f"🎯 إلى: {self.html(destination)}\n\n"
                             f"اضغط الرابط للذهاب للطلب.",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass  # تجاهل إذا لم يستطع الإرسال

    async def show_trip_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE, trip_id, pickup, destination, trip_type, price, maps_links, original_text):
        message = update.message
        user = update.effective_user

        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        extra = f"\n💰 <b>السعر:</b> {self.html(price)} ريال" if price else ""
        if maps_links:
            extra += "\n📍 <b>Google Maps:</b> مرفق"

        confirm_text = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>نوع المشوار:</b> {type_badge}
📝 <b>التفاصيل:</b>
{self.html(original_text)}
{extra}

🚕 <b>للكباتن:</b> اضغط الزر أدناه إذا كنت جاهزاً 👇
"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}")
        ]])

        await message.reply_text(confirm_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    # ---------- معالجات الأزرار ----------
    async def handle_take_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        driver = query.from_user
        try:
            data = query.data.split(":")
            trip_id, customer_id = int(data[1]), int(data[2])
        except (IndexError, ValueError):
            return

        if driver.id == customer_id:
            await query.answer("😂 ما تقدر تأخذ مشوارك بنفسك!", show_alert=True)
            return

        if not self.db.is_driver(driver.id):
            self.db.set_role(driver.id, "driver")

        self.db.add_ready_driver(trip_id, driver.id)

        trip = self.db.get_trip(trip_id)
        if not trip:
            return

        card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}
"""
        contact_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 تواصل مع العميل", callback_data=f"contact_customer:{trip_id}:{driver.id}")],
            [InlineKeyboardButton("🚕 تواصل مع الكابتن", callback_data=f"contact_driver:{trip_id}:{driver.id}")]
        ])

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=card_text,
            parse_mode=ParseMode.HTML,
            reply_markup=contact_keyboard
        )
        await query.answer("✅ تم إرسال بطاقتك وتأكيد جاهزيتك للمشوار!", show_alert=True)

    async def contact_customer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            data = query.data.split(":")
            trip_id, driver_id = int(data[1]), int(data[2])
        except (IndexError, ValueError):
            return

        trip = self.db.get_trip(trip_id)
        if not trip:
            return

        await query.answer("📩 فتح تواصل العميل...", url=f"tg://user?id={trip['customer_id']}")

    async def contact_driver(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user = query.from_user
        try:
            data = query.data.split(":")
            trip_id, driver_id = int(data[1]), int(data[2])
        except (IndexError, ValueError):
            return

        trip = self.db.get_trip(trip_id)
        if not trip or trip["customer_id"] != user.id:
            await query.answer("⚠️ مخصص لصاحب الطلب فقط.", show_alert=True)
            return

        await query.answer("🚕 فتح تواصل الكابتن...", url=f"tg://user?id={driver_id}")

    # ---------- الأوامر ----------
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(
                f"🚘 <b>{GROUP_NAME}</b>\n\n🤖 البوت يعمل ✅\n\n👤 <b>عميل:</b> اكتب مشوارك.\n🚕 <b>كابتن:</b> اكتب موقعك.",
                parse_mode=ParseMode.HTML
            )

    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(
                "🤖 <b>أوامر البوت:</b>\n"
                "/start - بدء البوت\n"
                "/rules - عرض القوانين\n"
                "/help - عرض المساعدة\n"
                "/stats - إحصائيات (للمشرفين فقط)\n\n"
                "💡 <b>للكباتن:</b> اكتب «أنا كابتن» ثم أرسل موقعك.\n"
                "💡 <b>للعملاء:</b> اكتب طلبك مباشرة مثل: من الحمدانية إلى الروضة.\n"
                "📍 يمكنك مشاركة موقعك مباشرة من تيليجرام.",
                parse_mode=ParseMode.HTML
            )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ هذا الأمر للمشرفين فقط.")
            return
        stats = self.db.get_stats()
        text = f"""
📊 <b>إحصائيات البوت</b>

👥 <b>إجمالي المستخدمين:</b> {stats['users']}
🚕 <b>السائقين:</b> {stats['drivers']}
👤 <b>العملاء:</b> {stats['customers']}
🚗 <b>إجمالي المشاوير:</b> {stats['trips']}
🔥 <b>المشاوير النشطة:</b> {stats['active_trips']}
"""
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    # ---------- تشغيل البوت ----------
    def run(self):
        if not TOKEN:
            raise RuntimeError("❌ BOT_TOKEN غير موجود.")
        app = Application.builder().token(TOKEN).build()

        # الأوامر
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("stats", self.cmd_stats))

        # الأزرار
        app.add_handler(CallbackQueryHandler(self.handle_take_trip, pattern=r"^take_trip:"))
        app.add_handler(CallbackQueryHandler(self.contact_customer, pattern=r"^contact_customer:"))
        app.add_handler(CallbackQueryHandler(self.contact_driver, pattern=r"^contact_driver:"))

        # الرسائل النصية والمواقع والصور
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.LOCATION, self.handle_message))
        app.add_handler(MessageHandler(filters.PHOTO & filters.CAPTION, self.handle_message))

        print("✅ البوت يعمل بنجاح وبذكاء متقدم...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SmartRidesBot()
    bot.run()
