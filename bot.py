"""
🤖 بوت مشاوير جدة الذكي - النسخة المتوافقة مع أحدث إصدارات مكتبة تيليجرام
"""

import os
import re
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ============================================================
# ⚙️ الإعدادات الأساسية
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "ضع_التوكن_هنا").strip()
GROUP_ID = -1001234567890  # ⚠️ ضع معرف قروبك هنا
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]  # ⚠️ ضع معرفك الرقمي هنا

SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

# ============================================================
# 📋 قوانين القروب
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب مخصص للمشاوير والنقل فقط.
2️⃣ يكتب العميل طلبه مباشرة.
3️⃣ 🚕 يضغط الكابتن على زر «أنا جاهز للمشوار» تحت الطلب.
4️⃣ 💰 يتم التفاهم على السعر بالخاص.
5️⃣ 🚫 يمنع الإعلان أو إرسال رسائل خارجية.
6️⃣ 🤝 الاحترام المتبادل واجب بين الجميع.

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🧠 الكلمات المفتاحية والمواقع
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "يومياً", "دوام", "مدرسة",
    "جامعة", "مشوار يومي", "توصيل يومي", "التزام", "اسبوعي", "أسبوعي",
    "شهر", "شهرين", "مداوم", "كل اسبوع", "كل أسبوع", "يومي", "شهرياً"
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني", "ابغى مشوار",
    "ابي مشوار", "احتاج توصيل", "ابغا مشوار", "من يوصلني", "اوصلني",
    "ودني", "خذني", "ابي", "أبي", "ابغا", "أبغا", "اريد", "أريد",
    "محتاج", "محتاجة", "أحتاج", "مين يوصل", "ابغى اروح", "ابي اروح"
]

PRESENCE_WORDS = [
    "متواجد", "موجود", "انا في", "أنا في", "انا عند", "أنا عند",
    "متوفر", "مستعد", "جاهز", "في الانتظار", "بالخدمة", "متواجده",
    "موجوده", "متواجدة", "موجودة", "واقف", "واقفه", "واقفة", "انتظر",
    "في الموقع", "بالموقع", "متاح", "متاحة"
]

LOCATIONS = [
    "الفضيلة", "الرغامة", "جدة", "مكة", "الرياض", "الدمام", "المدينة",
    "الطائف", "البلد", "البغدادية", "الروضة", "الصفا", "المروة", "النسيم",
    "السليمانية", "العزيزية", "الفيحاء", "الجامعة", "الحمراء", "الاندلس",
    "الأندلس", "الربوة", "النزهة", "المشرفة", "بني مالك", "الحمدانية",
    "السنابل", "المحمدية", "الزهراء", "الخالدية", "الصالحية", "النعيم",
    "الورود", "السلامة", "الشاطئ", "ابحر", "أبحر", "التوفيق",
    "العدل", "المنار", "الواحة", "الفيصلية", "الريان", "الوادي",
    "الفلاح", "النهضة", "الرابية", "الخزامى", "السلام مول", "السلام"
]

GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام",
    "صباح الخير", "صباح النور", "مساء الخير", "مساء النور",
    "هلا", "اهلا", "أهلا", "مرحبا", "ياهلا", "يا هلا", "مراحب"
]

# ============================================================
# 💾 إدارة قاعدة البيانات (SQLite)
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

    def add_memory(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO user_memory (user_id, message_text) VALUES (?, ?)", (user_id, text))
        self.conn.commit()

    def get_memory(self, user_id, limit=3):
        cur = self.conn.cursor()
        cur.execute("SELECT message_text FROM user_memory WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
        return [row["message_text"] for row in cur.fetchall()]

    def is_spam(self, user_id, text, within_seconds=30):
        cutoff = datetime.now() - timedelta(seconds=within_seconds)
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM anti_spam WHERE user_id = ? AND message_text = ? AND timestamp > ?",
                    (user_id, text, cutoff))
        return cur.fetchone()["cnt"] > 0

    def add_spam_record(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO anti_spam (user_id, message_text) VALUES (?, ?)", (user_id, text))
        self.conn.commit()

# ============================================================
# 🤖 آليات المعالجة والذكاء البرمجي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()

    def normalize_text(self, text):
        replacements = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ء": ""}
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def classify_intent(self, text, user_role, previous_messages=None):
        norm = self.normalize_text(text).strip()

        if any(g in norm for g in GREETINGS):
            return "greeting"
        if norm in ["انا كابتن", "كابتن", "سايق", "سواق"]:
            return "register_driver"
        if norm in ["انا عميل", "عميل", "زبون"]:
            return "register_customer"
        if any(w in norm for w in PRESENCE_WORDS):
            return "presence" if user_role == "driver" else "presence_not_driver"
        if self.looks_like_trip(text):
            return "trip"
        
        if previous_messages:
            last = previous_messages[0]
            if any(w in self.normalize_text(last) for w in ["من", "الى", "توصيل"]) and len(text) > 2:
                return "trip_detail"

        return "unknown"

    def looks_like_trip(self, text):
        norm = self.normalize_text(text)
        if any(w in norm for w in PRESENCE_WORDS):
            return False
        if any(w in norm for w in NORMAL_TRIP_WORDS + MONTHLY_TRIP_WORDS):
            return True
        if "من" in norm and ("الى" in norm or "الي" in norm or "إلى" in norm):
            return True
        locations_found = [loc for loc in LOCATIONS if self.normalize_text(loc) in norm]
        return len(locations_found) >= 2

    def extract_route(self, text):
        norm = self.normalize_text(text)
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي|لل|إلى)\s+(.+)", norm)
        if match:
            pickup = match.group(1).strip()
            dest = match.group(2).strip()
            return pickup, dest

        locations = [loc for loc in LOCATIONS if self.normalize_text(loc) in norm]
        if len(locations) >= 2:
            if any("السلام" in self.normalize_text(l) for l in locations):
                for i, l in enumerate(locations):
                    if "السلام" in self.normalize_text(l) and i > 0:
                        locations.insert(0, locations.pop(i))
            return locations[0], locations[1]
        
        return "موقع البداية", "الوجهة المطلوبة"

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
        if not text:
            return

        if self.db.is_spam(user.id, text):
            return
        self.db.add_spam_record(user.id, text)
        self.db.add_memory(user.id, text)

        role = self.db.get_role(user.id)
        previous = self.db.get_memory(user.id, limit=2)
        intent = self.classify_intent(text, role, previous)

        if intent == "greeting":
            await message.reply_text("وعليكم السلام ورحمة الله! 😊 أهلاً بك في مشاوير جدة، كيف يمكنني خدمتك اليوم؟")
            return

        if intent == "register_driver":
            self.db.set_role(user.id, "driver")
            await message.reply_text("✅ تم تسجيلك ككابتن بنجاح!\n📍 أرسل موقعك الحالي الآن لإعلان التواجد.")
            return

        if intent == "register_customer":
            self.db.set_role(user.id, "customer")
            await message.reply_text("✅ تم تسجيلك كعميل بنجاح!\nيمكنك الآن إرسال تفاصيل مشوارك.")
            return

        if intent == "presence":
            await message.reply_text("📍 تم تسجيل تواجدك في النظام بنجاح وجاهزيتك للمشاوير.")
            return

        if intent == "presence_not_driver":
            await message.reply_text("📝 يرجى التسجيل ككابتن أولاً عبر كتابة: (أنا كابتن).")
            return

        if intent in ["trip", "trip_detail"]:
            await self.handle_trip(update, context, text)
            return

        await message.reply_text("❓ عذراً، لم أفهم طلبك. هل ترغب في طلب مشوار أم إعلان تواجدك؟")

    async def handle_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        message = update.message
        user = update.effective_user

        pickup, destination = self.extract_route(text)
        trip_type = "monthly" if any(w in self.normalize_text(text) for w in MONTHLY_TRIP_WORDS) else "normal"

        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            original_text=text
        )

        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        card_text = f"""
✅ <b>تم تسجيل طلب المشوار بنجاح!</b>

📋 <b>النوع:</b> {type_badge}
📝 <b>التفاصيل:</b> {self.html(text)}

🚕 <b>للكباتن:</b> اضغط الزر أدناه عند الجاهزية للتنفيذ 👇
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}")],
            [InlineKeyboardButton("✅ تم المشوار", callback_data=f"close_trip:{trip_id}:{user.id}")]
        ])

        await message.reply_text(card_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    async def handle_take_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        driver = query.from_user
        try:
            _, trip_id, customer_id = query.data.split(":")
            trip_id, customer_id = int(trip_id), int(customer_id)
        except ValueError:
            return

        if driver.id == customer_id:
            await query.answer("😂 لا يمكنك أخذ مشوارك بنفسك!", show_alert=True)
            return

        self.db.add_ready_driver(trip_id, driver.id)
        trip = self.db.get_trip(trip_id)
        if not trip:
            return

        card_text = f"""
🚕 <b>تم تأكيد كابتن جاهز للمشوار!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 تواصل مع العميل", url=f"tg://user?id={trip['customer_id']}")],
            [InlineKeyboardButton("🚕 تواصل مع الكابتن", url=f"tg://user?id={driver.id}")]
        ])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=card_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        await query.answer("✅ تم إرسال جاهزيتك بنجاح!", show_alert=True)

    async def close_trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            _, trip_id, customer_id = query.data.split(":")
            trip_id, customer_id = int(trip_id), int(customer_id)
        except ValueError:
            return

        if query.from_user.id != customer_id:
            await query.answer("⚠️ إغلاق المشوار مخصص لصاحب الطلب فقط.", show_alert=True)
            return

        self.db.close_trip(trip_id)
        await query.edit_message_text("✅ تم إغلاق المشوار بنجاح، شكراً لاستخدامكم البوت.")

    def run(self):
        if not TOKEN or TOKEN == "ضع_التوكن_هنا":
            print("❌ تنبيه: يرجى وضع توكن البوت الصحيح في المتغير TOKEN.")
            return

        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text(f"🚘 أهلاً بك في {GROUP_NAME}\nالبوت يعمل بكفاءة عالية.")))
        app.add_handler(CommandHandler("rules", lambda u, c: u.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)))
        
        app.add_handler(CallbackQueryHandler(self.handle_take_trip, pattern=r"^take_trip:"))
        app.add_handler(CallbackQueryHandler(self.close_trip, pattern=r"^close_trip:"))
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        print("✅ تم تشغيل بوت مشاوير جدة بنجاح واستقرار تام...")
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SmartRidesBot()
    bot.run()
