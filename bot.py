"""
🤖 بوت مشاوير جدة الذكي - النسخة المطورة والمحدثة (بدون تكرار ومع إرسال البطاقة فوراً)
"""

import os
import re
import random
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
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

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()

GROUP_ID = -1001234567890
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]

SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

ENGAGEMENT_INTERVAL = 45 * 60

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
# 🧠 كلمات المشاوير
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "يومياً", "دوام", "مدرسة",
    "جامعة", "مشوار يومي", "توصيل يومي", "التزام", "مكان المنزل",
    "مكان الدوام", "عدد الايام", "عدد ايام الدوام", "اسبوعي", "أسبوعي",
    "شهر", "شهرين", "راتب", "مداوم", "كل اسبوع", "كل أسبوع",
    "monthly", "month", "daily", "every day", "everyday",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني", "ابغى مشوار",
    "ابي مشوار", "احتاج توصيل", "ابغا مشوار", "من يوصلني", "فيه كابتن",
    "اوصلني", "ودني", "خذني", "نبغى", "نبي", "ابي", "أبي", "ابغا",
    "أبغا", "اريد", "أريد", "عايز", "محتاج", "محتاجة",
    "trip", "ride", "from", "to", "need", "pickup",
]

PRESENCE_WORDS = [
    "متواجد", "موجود", "انا في", "أنا في", "انا عند", "أنا عند",
    "متوفر", "مستعد", "جاهز", "في الانتظار", "بالخدمة", "متواجده",
    "موجوده", "متواجدة", "موجودة", "available", "here", "ready",
    "present", "online", "واقف", "واقفه", "واقفة", "انتظر", "مستني",
    "في الموقع", "بالموقع", "متجهز", "متجهزة",
]

LOCATIONS = [
    "الفضيلة", "الرغامة", "جدة", "مكة", "الرياض", "الدمام", "المدينة",
    "الطائف", "أبها", "تبوك", "جازان", "الجنوب", "الشمال", "الشرق",
    "الغرب", "البلد", "البغدادية", "الروضة", "الصفا", "المروة", "النسيم",
    "السليمانية", "العزيزية", "الفيحاء", "الجامعة", "الحمراء", "الاندلس",
    "الأندلس", "الربوة", "النزهة", "المشرفة", "بني مالك", "الهدا",
    "الشفا", "الحمدانية", "السنابل", "المداين", "السالم",
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
    (["شسمك"], "اسمي بوت المشاوير 😎"),
    (["طفشان", "ملل"], ["اطلب مشوار وتروق 🚘"]),
    (["احبك", "حبيبي"], ["حبيبي أنت 🌹"]),
    (["كم السعر"], ["💰 السعر بالتفاهم 🤝"]),
    (["بوت", "يا بوت"], ["نعم أنا هنا 🤖"]),
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    role TEXT DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    customer_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    original_text TEXT DEFAULT '',
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS driver_presence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER UNIQUE,
                    location TEXT,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            con.commit()

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

    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            # استخدام INSERT OR IGNORE لتفادي أخطاء التكرار مع الحفاظ على استمرارية التنفيذ
            cur.execute("""
                INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id)
                VALUES (?, ?)
            """, (trip_id, driver_id))
            con.commit()

    def set_presence(self, driver_id, location):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO driver_presence (driver_id, location)
                VALUES (?, ?)
                ON CONFLICT(driver_id) DO UPDATE SET
                    location = excluded.location,
                    last_update = CURRENT_TIMESTAMP
            """, (driver_id, location))
            con.commit()

# ============================================================
# 🤖 البوت
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
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def detect_trip_type(self, text):
        normalized = self.normalize_text(text)
        for word in MONTHLY_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "monthly"
        for word in NORMAL_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "normal"
        if re.search(r"من\s+.+?\s+(?:الى|الي|لل)\s+.+", normalized, re.IGNORECASE):
            return "normal"
        return None

    def detect_presence(self, text):
        normalized = self.normalize_text(text)
        for word in PRESENCE_WORDS:
            if self.normalize_text(word) in normalized:
                return True
        return False

    def extract_location(self, text):
        normalized = self.normalize_text(text)
        for loc in LOCATIONS:
            if self.normalize_text(loc) in normalized:
                return loc
        return None

    def looks_like_trip(self, text):
        normalized = self.normalize_text(text)
        if self.detect_presence(text):
            route_exists = bool(re.search(r"من\s+.+?\s+(?:الى|الي|لل)\s+.+", normalized, re.IGNORECASE))
            if not route_exists and not any(w in normalized for w in ["ابغى", "ابي", "احتاج", "يوصلني", "مشوار", "توصيل"]):
                return False
        if self.detect_trip_type(text):
            return True
        if re.search(r"من\s+.+?\s+(?:الى|الي|لل)\s+.+", normalized, re.IGNORECASE):
            return True
        return False

    def extract_route(self, text):
        normalized = self.normalize_text(text)
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي|لل)\s+(.+)", normalized, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return "غير محدد", "غير محدد"

    def extract_price(self, text):
        match = re.search(r"(?:السعر|سعر|المبلغ|بـ|ب)\s*[:：]?\s*(\d+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_maps_links(self, text):
        return re.findall(r"https?://(?:www\.)?(?:google\.[^/\s]+|maps\.google\.[^/\s]+)[^\s<>]+", text, re.IGNORECASE)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        if not message or not user:
            return

        self.db.save_user(user)
        text = message.text or message.caption or ""
        if not text:
            return

        normalized_text = self.normalize_text(text).strip()

        # 1️⃣ تسجيل كابتن
        if normalized_text in ["انا كابتن", "انا سايق", "انا سواق", "كابتن"]:
            self.db.set_role(user.id, "driver")
            await message.reply_text(
                "✅ <b>تم تسجيلك ككابتن بنجاح!</b>\n\n"
                "لن يُطلب منك التسجيل مرة أخرى. 👍\n\n"
                "📍 أعلن موقعك مثل:\nأنا متواجد في الحمدانية",
                parse_mode=ParseMode.HTML
            )
            return

        # 2️⃣ تسجيل عميل
        if normalized_text in ["انا عميل", "انا زبون", "عميل"]:
            self.db.set_role(user.id, "customer")
            await message.reply_text(
                "✅ <b>تم تسجيلك كعميل بنجاح!</b>\n\n"
                "الآن اكتب مشوارك مباشرة 🚗\nمثال: من الفضيلة إلى الرغامة",
                parse_mode=ParseMode.HTML
            )
            return

        # 3️⃣ التواجد (خاص بالكابتن)
        if self.detect_presence(text):
            role = self.db.get_role(user.id)
            if role == "driver":
                location = self.extract_location(text) or "غير محدد"
                self.db.set_presence(user.id, location)
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
            elif role != "driver" and not self.looks_like_trip(text):
                await message.reply_text(
                    "📝 <b>سجل نوعك أولاً لكي تتمكن من إعلان التواجد!</b>\n\n"
                    "🚕 للكابتن: اكتب «أنا كابتن»\n👤 للعميل: اكتب «أنا عميل»",
                    parse_mode=ParseMode.HTML
                )
                return

        # 4️⃣ طلب مشوار
        if self.looks_like_trip(text):
            if self.db.is_driver(user.id):
                if not any(w in normalized_text for w in ["ابغى", "ابي", "احتاج", "يوصلني", "يوديني", "من يوصلني"]):
                    return
            await self.handle_trip_request(update, context, text)
            return

    async def handle_trip_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text):
        message = update.message
        user = update.effective_user
        pickup, destination = self.extract_route(text)
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

        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        extra = f"\n💰 <b>السعر:</b> {self.html(price)} ريال" if price else ""
        if maps_links:
            extra += "\n📍 <b>Google Maps:</b> مرفق"

        confirm_text = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>نوع المشوار:</b> {type_badge}
📝 <b>التفاصيل:</b>
{self.html(text)}
{extra}

🚕 <b>للكباتن:</b> اضغط الزر أدناه إذا كنت جاهزاً 👇
"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}")
        ]])

        await message.reply_text(confirm_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

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

        # تسجيل الكابتن وإرسال البطاقة للقروب مباشرة ودون توقف
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

        # إرسال بطاقة الكابتن إلى القروب في كل مرة يضغط فيها على الزر
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=card_text,
            parse_mode=ParseMode.HTML,
            reply_markup=contact_keyboard
        )
        await query.answer("✅ تم إرسال بطاقتك وتأكيد جاهزيتك للمشوار!", show_alert=True)

    async def contact_customer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user = query.from_user
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
            await update.message.reply_text("🤖 استخدم /start لبدء البوت أو اكتب طلبك مباشرة.", parse_mode=ParseMode.HTML)

    def run(self):
        if not TOKEN:
            raise RuntimeError("❌ BOT_TOKEN غير موجود.")
        app = Application.builder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CallbackQueryHandler(self.handle_take_trip, pattern=r"^take_trip:"))
        app.add_handler(CallbackQueryHandler(self.contact_customer, pattern=r"^contact_customer:"))
        app.add_handler(CallbackQueryHandler(self.contact_driver, pattern=r"^contact_driver:"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        print("✅ البوت يعمل بنجاح بدون تكرار وبحفظ دائم للقاعدة...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SmartRidesBot()
    bot.run()
