"""
🤖 بوت مشاوير جدة الذكي - النسخة النهائية المتكاملة
"""

import os
import re
import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "ضع_التوكن_هنا").strip()
GROUP_ID = -1001234567890  # ⚠️ غيّره إلى معرف قروبك
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]  # ⚠️ ضع معرفك الرقمي هنا

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
# 🧠 قوائم الكلمات (موسّعة)
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

# عبارات السلام والمجاملات
GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام",
    "صباح الخير", "صباح النور", "مساء الخير", "مساء النور",
    "هلا", "اهلا", "أهلا", "مرحبا", "هاي", "هلو",
    "ياهلا", "يا هلا", "مراحب", "تحية طيبة", "تحياتي",
    "كيف الحال", "كيفك", "كيفكم", "شخبارك", "شخباركم",
    "شكرا", "شكراً", "يعطيك العافية", "تسلم", "بارك الله فيك",
    "جزاك الله خير", "مشكور", "مشكورة"
]

# ============================================================
# 💾 قاعدة البيانات
# ============================================================

import sqlite3

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            role TEXT DEFAULT '',
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS trips (
            trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            customer_id INTEGER,
            pickup TEXT,
            destination TEXT,
            trip_type TEXT DEFAULT 'normal',
            original_text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS ready_drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER,
            driver_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trip_id, driver_id)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS driver_presence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver_id INTEGER UNIQUE,
            location TEXT,
            latitude REAL,
            longitude REAL,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS anti_spam (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            reason TEXT
        )""")
        self.conn.commit()

    def save_user(self, user):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, name, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                username = excluded.username
        """, (user.id, user.full_name, user.username or ""))
        self.conn.commit()

    def set_role(self, user_id, role):
        cur = self.conn.cursor()
        cur.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        self.conn.commit()

    def get_role(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["role"] if row else ""

    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"

    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"

    def ban_user(self, user_id, reason=""):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO banned_users (user_id, reason) VALUES (?, ?)", (user_id, reason))
        self.conn.commit()

    def unban_user(self, user_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_banned(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        return cur.fetchone() is not None

    def create_trip(self, message_id, customer_id, pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, pickup, destination, trip_type, original_text)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, customer_id, pickup, destination, trip_type, original_text))
        self.conn.commit()
        return cur.lastrowid

    def get_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE trips SET status = 'closed' WHERE trip_id = ?", (trip_id,))
        self.conn.commit()

    def add_ready_driver(self, trip_id, driver_id):
        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id) VALUES (?, ?)", (trip_id, driver_id))
        self.conn.commit()

    def set_presence(self, driver_id, location, latitude=None, longitude=None):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO driver_presence (driver_id, location, latitude, longitude)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(driver_id) DO UPDATE SET
                location = excluded.location,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                last_update = CURRENT_TIMESTAMP
        """, (driver_id, location, latitude, longitude))
        self.conn.commit()

    def get_presence(self, driver_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM driver_presence WHERE driver_id = ?", (driver_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_all_presences(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM driver_presence ORDER BY last_update DESC")
        return [dict(row) for row in cur.fetchall()]

    def add_memory(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO user_memory (user_id, message_text) VALUES (?, ?)", (user_id, text))
        self.conn.commit()
        cur.execute("""
            DELETE FROM user_memory WHERE user_id = ? AND id NOT IN (
                SELECT id FROM user_memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5
            )
        """, (user_id, user_id))
        self.conn.commit()

    def get_memory(self, user_id, limit=5):
        cur = self.conn.cursor()
        cur.execute("SELECT message_text FROM user_memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        rows = cur.fetchall()
        return [row["message_text"] for row in rows]

    def is_spam(self, user_id, text, within_seconds=60):
        cutoff = datetime.now() - timedelta(seconds=within_seconds)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM anti_spam WHERE user_id = ? AND message_text = ? AND timestamp > ?",
                    (user_id, text, cutoff))
        return cur.fetchone()["cnt"] > 0

    def add_spam_record(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO anti_spam (user_id, message_text) VALUES (?, ?)", (user_id, text))
        self.conn.commit()

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
# 🤖 البوت الذكي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()

    def normalize_text(self, text):
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
            "ؤ": "و", "ئ": "ي", "ء": "", "ٱ": "ا", "ڪ": "ك",
            "ﮐ": "ك", "ڿ": "ك",
        }
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.replace("from", "من").replace("to", "الى")
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def is_greeting(self, text):
        norm = self.normalize_text(text).strip()
        return any(greet in norm for greet in GREETINGS)

    def classify_intent(self, text, user_role, previous_messages=None):
        norm = self.normalize_text(text).strip()

        # التحقق من التحية أولاً
        if self.is_greeting(text):
            return "greeting"

        if norm in ["انا كابتن", "انا سايق", "انا سواق", "كابتن", "سايق", "سواق", "انا سائق"]:
            return "register_driver"
        if norm in ["انا عميل", "انا زبون", "عميل", "زبون", "انا راكب"]:
            return "register_customer"

        if self.detect_presence(text):
            return "presence" if user_role == "driver" else "presence_not_driver"

        if self.looks_like_trip(text):
            return "trip"

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
        locations_found = [loc for loc in LOCATIONS if self.normalize_text(loc) in norm]
        return len(locations_found) >= 2

    def extract_location(self, text):
        norm = self.normalize_text(text)
        for loc in LOCATIONS:
            if self.normalize_text(loc) in norm:
                return loc
        match = re.search(r"(?:في|عند|بـ|قرب|داخل)\s+([\w\s]+)", norm)
        if match:
            return match.group(1).strip()
        return None

    def extract_route(self, text):
        norm = self.normalize_text(text)
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي|لل|إلى)\s+(.+)", norm)
        if match:
            return match.group(1).strip(), match.group(2).strip()
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

    def extract_maps_links(self, text):
        return re.findall(r"https?://(?:www\.)?(?:google\.[^/\s]+|maps\.google\.[^/\s]+)[^\s<>]+", text, re.IGNORECASE)

    # ---------- معالجة الرسائل ----------
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        if not message or not user:
            return
        self.db.save_user(user)

        if self.db.is_banned(user.id):
            await message.reply_text("⛔️ أنت محظور من استخدام البوت.")
            return

        text = message.text or message.caption or ""
        location_data = None
        if message.location:
            loc = message.location
            text = f"موقعي {loc.latitude}, {loc.longitude}"
            location_data = loc

        if not text:
            return

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

        if intent == "greeting":
            greetings_responses = [
                "وعليكم السلام ورحمة الله وبركاته! 😊",
                "أهلاً وسهلاً! كيف أقدر أساعدك اليوم؟",
                "مرحباً! أنا بوت المشاوير، تفضل بطلبك.",
                "هلا والله! 🙋‍♂️",
                "وعليكم السلام! أتمنى لك يوم سعيد."
            ]
            await message.reply_text(random.choice(greetings_responses), parse_mode=ParseMode.HTML)
            return

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

        if intent == "presence":
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
            last_trip_text = previous[0] if previous else ""
            pickup, destination = self.extract_route(last_trip_text)
            new_location = self.extract_location(text) or text.strip()
            if not pickup:
                pickup = new_location
            elif not destination:
                destination = new_location
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

        if not pickup or not destination:
            if not pickup and not destination:
                await message.reply_text("من فضلك حدد نقطة الانطلاق والوجهة.\nمثال: من الحمدانية إلى البلد")
            elif not pickup:
                await message.reply_text("من أين ستنطلق؟")
            else:
                await message.reply_text("إلى أين تريد الذهاب؟")
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

⚠️ <b>تنبيه هام:</b> لا تتعامل مع الكباتن الذين لم يسجلوا جاهزين، حفاظاً على سلامتك.

🚕 <b>للكباتن:</b> اضغط الزر أدناه إذا كنت جاهزاً 👇
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}")],
            [InlineKeyboardButton("✅ تم المشوار", callback_data=f"close_trip:{trip_id}:{user.id}")]
        ])

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

    async def close_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            data = query.data.split(":")
            trip_id, customer_id = int(data[1]), int(data[2])
        except (IndexError, ValueError):
            return

        if query.from_user.id != customer_id:
            await query.answer("⚠️ مخصص لصاحب الطلب فقط.", show_alert=True)
            return

        self.db.close_trip(trip_id)
        await query.edit_message_text("✅ تم إغلاق المشوار بنجاح.")

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
        await update.message.reply_text(
            f"🚘 <b>{GROUP_NAME}</b>\n\n🤖 البوت يعمل ✅\n\n👤 <b>عميل:</b> اكتب مشوارك.\n🚕 <b>كابتن:</b> اكتب موقعك.",
            parse_mode=ParseMode.HTML
        )

    async def cmd_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 <b>أوامر البوت:</b>\n"
            "/start - بدء البوت\n"
            "/rules - عرض القوانين\n"
            "/help - عرض المساعدة\n"
            "/stats - إحصائيات (للمشرفين)\n"
            "/ban - حظر مستخدم (رد على رسالته)\n"
            "/unban - فك حظر مستخدم\n\n"
            "💡 <b>للكباتن:</b> اكتب «أنا كابتن» ثم أرسل موقعك.\n"
            "💡 <b>للعملاء:</b> اكتب طلبك مباشرة.\n"
            "📍 يمكنك مشاركة موقعك مباشرة من تيليجرام.",
            parse_mode=ParseMode.HTML
        )

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ هذا الأمر للمشرفين فقط.")
            return
        stats = self.db.get_stats()
        text = f"""
📊 <b>إحصائيات البوت</b>

👥 <b>المستخدمون:</b> {stats['users']}
🚕 <b>السائقون:</b> {stats['drivers']}
👤 <b>العملاء:</b> {stats['customers']}
🚗 <b>المشاوير:</b> {stats['trips']}
🔥 <b>النشطة:</b> {stats['active_trips']}
"""
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)

    async def cmd_ban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ هذا الأمر للمشرفين فقط.")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("استخدم الأمر بالرد على رسالة المستخدم.")
            return
        target = update.message.reply_to_message.from_user.id
        self.db.ban_user(target, "مخالفة")
        await update.message.reply_text(f"✅ تم حظر المستخدم {target}.")

    async def cmd_unban(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔️ هذا الأمر للمشرفين فقط.")
            return
        if not context.args:
            await update.message.reply_text("استخدم: /unban <user_id>")
            return
        target = int(context.args[0])
        self.db.unban_user(target)
        await update.message.reply_text(f"✅ تم فك حظر المستخدم {target}.")

    # ---------- تشغيل ----------
    def run(self):
        if not TOKEN:
            raise RuntimeError("❌ BOT_TOKEN غير موجود.")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("stats", self.cmd_stats))
        app.add_handler(CommandHandler("ban", self.cmd_ban))
        app.add_handler(CommandHandler("unban", self.cmd_unban))

        app.add_handler(CallbackQueryHandler(self.handle_take_trip, pattern=r"^take_trip:"))
        app.add_handler(CallbackQueryHandler(self.close_trip, pattern=r"^close_trip:"))
        app.add_handler(CallbackQueryHandler(self.contact_customer, pattern=r"^contact_customer:"))
        app.add_handler(CallbackQueryHandler(self.contact_driver, pattern=r"^contact_driver:"))

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.LOCATION, self.handle_message))

        print("✅ البوت يعمل بنجاح وبذكاء متقدم...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SmartRidesBot()
    bot.run()
