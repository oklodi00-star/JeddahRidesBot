"""
🤖 بوت مشاوير جدة الذكي - النسخة النهائية
"""

import os
import re
import logging
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# محاولة استيراد flashgeotext لتحسين المواقع
try:
    from flashgeotext.geotext import GeoText
    GEO_TEXT_AVAILABLE = True
except ImportError:
    GEO_TEXT_AVAILABLE = False

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "ضع_التوكن_هنا").strip()
GROUP_ID = -1001234567890  # غيّره إلى معرف قروبك
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]  # أضف معرفك

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

# قاعدة البيانات: اختر "sqlite" أو "postgres"
DB_TYPE = "sqlite"
DB_FILE = "smart_rides.db"  # لـ SQLite
DATABASE_URL = "postgresql://user:pass@host:port/dbname"  # لـ PostgreSQL

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
# 🧠 كلمات ومفردات (موسّعة)
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
# 💾 قاعدة البيانات (تدعم SQLite و PostgreSQL)
# ============================================================

class Database:
    def __init__(self):
        self.db_type = DB_TYPE
        if self.db_type == "sqlite":
            import sqlite3
            self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        else:
            import psycopg2
            import psycopg2.extras
            self.conn = psycopg2.connect(DATABASE_URL)
            self.conn.row_factory = psycopg2.extras.RealDictCursor
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT,
                username TEXT,
                role TEXT DEFAULT '',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id SERIAL PRIMARY KEY,
                message_id BIGINT UNIQUE,
                customer_id BIGINT,
                pickup TEXT,
                destination TEXT,
                trip_type TEXT DEFAULT 'normal',
                original_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ready_drivers (
                id SERIAL PRIMARY KEY,
                trip_id BIGINT,
                driver_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trip_id, driver_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS driver_presence (
                id SERIAL PRIMARY KEY,
                driver_id BIGINT UNIQUE,
                location TEXT,
                latitude REAL,
                longitude REAL,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                message_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS anti_spam (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                message_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id BIGINT PRIMARY KEY,
                reason TEXT
            )
        """)
        self.conn.commit()

    # ---------- دوال عامة ----------
    def save_user(self, user):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, name, username)
            VALUES (%s, %s, %s)
            ON CONFLICT(user_id) DO UPDATE SET
                name = EXCLUDED.name,
                username = EXCLUDED.username
        """, (user.id, user.full_name, user.username or ""))
        self.conn.commit()

    def set_role(self, user_id, role):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
        self.conn.commit()

    def get_role(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        return row["role"] if row else ""

    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"

    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"

    def ban_user(self, user_id, reason=""):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO banned_users (user_id, reason) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_id, reason))
        self.conn.commit()

    def unban_user(self, user_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM banned_users WHERE user_id = %s", (user_id,))
        self.conn.commit()

    def is_banned(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM banned_users WHERE user_id = %s", (user_id,))
        return cur.fetchone() is not None

    # ---------- مشاوير ----------
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, pickup, destination, trip_type, original_text)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING trip_id
        """, (message_id, customer_id, pickup, destination, trip_type, original_text))
        trip_id = cur.fetchone()["trip_id"]
        self.conn.commit()
        return trip_id

    def get_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE trips SET status = 'closed' WHERE trip_id = %s", (trip_id,))
        self.conn.commit()

    def add_ready_driver(self, trip_id, driver_id):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO ready_drivers (trip_id, driver_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (trip_id, driver_id))
        self.conn.commit()

    # ---------- تواجد ----------
    def set_presence(self, driver_id, location, latitude=None, longitude=None):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO driver_presence (driver_id, location, latitude, longitude)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(driver_id) DO UPDATE SET
                location = EXCLUDED.location,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                last_update = CURRENT_TIMESTAMP
        """, (driver_id, location, latitude, longitude))
        self.conn.commit()

    def get_presence(self, driver_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM driver_presence WHERE driver_id = %s", (driver_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_presences(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM driver_presence ORDER BY last_update DESC")
        return [dict(row) for row in cur.fetchall()]

    # ---------- ذاكرة قصيرة ----------
    def add_memory(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO user_memory (user_id, message_text) VALUES (%s, %s)", (user_id, text))
        self.conn.commit()
        # نحتفظ بآخر 5 رسائل
        cur.execute("""
            DELETE FROM user_memory WHERE user_id = %s AND id NOT IN (
                SELECT id FROM user_memory WHERE user_id = %s ORDER BY timestamp DESC LIMIT 5
            )
        """, (user_id, user_id))
        self.conn.commit()

    def get_memory(self, user_id, limit=5):
        cur = self.conn.cursor()
        cur.execute("SELECT message_text FROM user_memory WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s", (user_id, limit))
        rows = cur.fetchall()
        return [row["message_text"] for row in rows]

    # ---------- منع السبام ----------
    def is_spam(self, user_id, text, within_seconds=60):
        cutoff = datetime.now() - timedelta(seconds=within_seconds)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM anti_spam WHERE user_id = %s AND message_text = %s AND timestamp > %s",
                    (user_id, text, cutoff))
        return cur.fetchone()["cnt"] > 0

    def add_spam_record(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO anti_spam (user_id, message_text) VALUES (%s, %s)", (user_id, text))
        self.conn.commit()

    # ---------- إحصائيات ----------
    def get_stats(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        users = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'driver'")
        drivers = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'")
        customers = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM trips")
        trips = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) as cnt FROM trips WHERE status = 'active'")
        active_trips = cur.fetchone()["cnt"]
        return {"users": users, "drivers": drivers, "customers": customers, "trips": trips, "active_trips": active_trips}

# ============================================================
# 🤖 البوت
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()

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
        # ترجمة إنجليزية بسيطة
        text = text.replace("from", "من").replace("to", "الى")
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ---------- تحليل النوايا ----------
    def classify_intent(self, text, user_role, previous_messages=None):
        norm = self.normalize_text(text).strip()

        # تسجيل
        if norm in ["انا كابتن", "انا سايق", "انا سواق", "كابتن", "سايق", "سواق", "انا سائق"]:
            return "register_driver"
        if norm in ["انا عميل", "انا زبون", "عميل", "زبون", "انا راكب"]:
            return "register_customer"

        # تواجد
        if self.detect_presence(text):
            return "presence" if user_role == "driver" else "presence_not_driver"

        # طلب مشوار
        if self.looks_like_trip(text):
            return "trip"

        # استخدام السياق
        if previous_messages:
            last = previous_messages[0] if previous_messages else ""
            if self.looks_like_trip(last) and self.extract_location(text):
                return "trip_detail"
            if self.detect_presence(last) and self.extract_location(text):
                return "presence_detail"

        return "unknown"

    def detect_presence(self, text):
        norm = self.normalize_text(text)
        return any(w in norm for w in PRESENCE_WORDS)

    def detect_trip_type(self, text):
        norm = self.normalize_text(text)
        if any(w in norm for w in MONTHLY_TRIP_WORDS):
            return "monthly"
        if any(w in norm for w in NORMAL_TRIP_WORDS):
            return "normal"
        if re.search(r"من\s+.+?\s+(?:الى|الي|لل|إلى)\s+.+", norm):
            return "normal"
        return None

    def looks_like_trip(self, text):
        norm = self.normalize_text(text)
        if self.detect_presence(text):
            return False
        if self.detect_trip_type(text):
            return True
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
        if any(re.search(p, norm) for p in patterns):
            return True
        # مكانين أو أكثر
        locations_found = [loc for loc in LOCATIONS if self.normalize_text(loc) in norm]
        return len(locations_found) >= 2

    def extract_location(self, text):
        # استخدام flashgeotext إن وجد
        if GEO_TEXT_AVAILABLE:
            geotext = GeoText()
            places = geotext.extract(input_text=text)
            if places:
                return list(places.keys())[0]
        # قائمة المواقع
        norm = self.normalize_text(text)
        for loc in LOCATIONS:
            if self.normalize_text(loc) in norm:
                return loc
        # نمط "في ..."
        match = re.search(r"(?:في|عند|بـ|قرب|داخل)\s+([\w\s]+)", norm)
        if match:
            return match.group(1).strip()
        return None

    def extract_route(self, text):
        norm = self.normalize_text(text)
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي|لل|إلى)\s+(.+)", norm)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        # قائمة المواقع
        locations = [loc for loc in LOCATIONS if self.normalize_text(loc) in norm]
        if len(locations) >= 2:
            return locations[0], locations[1]
        return None, None

    def extract_price(self, text):
        patterns = [
            r"(?:السعر|سعر|المبلغ|بـ|ب)\s*[:：]?\s*(\d+)\s*(?:ريال|ر\.س|SAR)?",
            r"(\d+)\s*(?:ريال|ر\.س|SAR)"
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    # ---------- معالجة الرسائل ----------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        if not message or not user:
            return
        self.db.save_user(user)

        # التحقق من الحظر
        if self.db.is_banned(user.id):
            await message.reply_text("⛔️ أنت محظور من استخدام البوت.")
            return

        text = message.text or message.caption or ""
        if message.location:
            loc = message.location
            text = f"موقعي {loc.latitude}, {loc.longitude}"
            location_data = loc
        else:
            location_data = None

        if not text:
            return

        # منع السبام
        if self.db.is_spam(user.id, text):
            return
        self.db.add_spam_record(user.id, text)
        self.db.add_memory(user.id, text)

        state = context.user_data.get("state")

        # ---------- معالجة الحالات ----------
        if state == "awaiting_location":
            location = self.extract_location(text)
            if location_data:
                location = f"{location_data.latitude:.4f}, {location_data.longitude:.4f}"
            elif not location:
                location = text.strip()
            self.db.set_presence(user.id, location,
                                 latitude=location_data.latitude if location_data else None,
                                 longitude=location_data.longitude if location_data else None)
            await message.reply_text(f"✅ تم تسجيل تواجدك في {self.html(location)}", parse_mode=ParseMode.HTML)
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
                    await message.reply_text("يجب التسجيل ككابتن أولاً.")
                return
            elif choice in ["3", "تسجيل"]:
                context.user_data.pop("state", None)
                await message.reply_text("اختر نوع التسجيل:\n1️⃣ كابتن\n2️⃣ عميل")
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
                await message.reply_text("✅ تم تسجيلك ككابتن!\n📍 أرسل موقعك الحالي.")
                context.user_data["state"] = "awaiting_location"
                return
            elif choice in ["2", "عميل"]:
                self.db.set_role(user.id, "customer")
                context.user_data.pop("state", None)
                await message.reply_text("✅ تم تسجيلك كعميل!\nالآن اكتب مشوارك مباشرة.")
                return
            else:
                await message.reply_text("اختيار غير صحيح، اختر 1 أو 2.")
                return

        # ---------- معالجة النية ----------
        role = self.db.get_role(user.id)
        previous = self.db.get_memory(user.id, limit=3)
        intent = self.classify_intent(text, role, previous)

        if intent == "register_driver":
            if role == "driver":
                await message.reply_text("أنت مسجل ككابتن بالفعل ✅\nأرسل موقعك الحالي مباشرة.")
                context.user_data["state"] = "awaiting_location"
            else:
                self.db.set_role(user.id, "driver")
                await message.reply_text("✅ تم تسجيلك ككابتن بنجاح!\n📍 أعلن موقعك مثل: أنا متواجد في الحمدانية")
                context.user_data["state"] = "awaiting_location"
            return

        if intent == "register_customer":
            if role == "customer":
                await message.reply_text("أنت مسجل كعميل بالفعل ✅\nاكتب مشوارك.")
            else:
                self.db.set_role(user.id, "customer")
                await message.reply_text("✅ تم تسجيلك كعميل بنجاح!\nالآن اكتب مشوارك مباشرة.")
            return

        if intent == "pres
