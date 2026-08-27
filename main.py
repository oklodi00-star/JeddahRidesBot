"""
🤖 بوت مشاوير جدة الذكي - النسخة النهائية
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

TOKEN = "8881485708:AAGxUH3xKk7kKQ8rKkW6lMKxxtV72klS5O8"

GROUP_ID = -1001234567890  # ⚠️ ضع ايدي القروب هنا
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

OWNER_ID = 952638746
ADMIN_USERNAME = "klodi500"
ADMIN_USERNAMES = ["klodi500"]
ADMIN_IDS = [952638746]  # ⚠️ أضف ايديك هنا

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides.db"

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
# 🧠 كلمات ذكية
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "دوام", "مدرسة", "جامعة",
    "مشوار يومي", "توصيل يومي", "التزام", "مكان المنزل", "مكان الدوام",
    "لوكيشن", "عدد الايام", "عدد ايام الدوام",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني",
    "ابغى مشوار", "ابي مشوار", "احتاج توصيل",
    "من يوصلني", "فيه كابتن", "اوصلني", "ودني",
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
    (["شسمك"], ["اسمي بوت المشاوير 😎"]),
    (["طفشان", "ملل"], ["اطلب مشوار وتروق 🚘"]),
    (["احبك", "حبيبي"], ["حبيبي أنت 🌹"]),
    (["كم السعر"], ["💰 السعر بالتفاهم 🤝"]),
    (["بوت", "يا بوت"], ["نعم أنا هنا 🤖"]),
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
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal"):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips 
                (message_id, customer_id, pickup, destination, trip_type)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type))
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
# 🤖 البوت الرئيسي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()
    
    def normalize_text(self, text):
        replacements = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}
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
                if normalized.startswith(self.normalize_text(phrase)):
                    return random.choice(responses)
        return None
    
    async def welcome_new_member(self, update, context):
        message = update.message
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            self.db.save_user(member)
            welcome_text = f"""
🌟 <b>يا هلا {self.html(member.full_name)}!</b>

نورت <b>{GROUP_NAME}</b> 🚘

👤 <b>عميل:</b> اكتب طلبك مباشرة
🚕 <b>كابتن:</b> اضغط زر «أنا جاهز» تحت الطلب

✍️ <b>للتسجيل:</b> اكتب «أنا كابتن» أو «أنا عميل»
            """
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👤 أنا عميل", callback_data=f"role_customer:{member.id}"),
                    InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"role_driver:{member.id}"),
                ],
                [
                    InlineKeyboardButton("📋 قانون القروب", callback_data="rules"),
                    InlineKeyboardButton("📩 الإدارة", url=f"https://t.me/{ADMIN_USERNAME}"),
                ],
            ])
            await message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    async def role_selection(self, update, context):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        
        if data.startswith("role_customer:"):
            role = "customer"
            role_text = "✅ <b>تم تسجيله كعميل!</b>"
        elif data.startswith("role_driver:"):
            role = "driver"
            role_text = "✅ <b>تم تسجيله ككابتن!</b>"
        else:
            return
        
        target_id = int(data.split(":")[1])
        
        # ✅ السماح للأدمن بالتصنيف
        is_admin = False
        try:
            member = await context.bot.get_chat_member(GROUP_ID, user.id)
            is_admin = member.status in ["administrator", "creator"]
        except:
            pass
        
        if user.id != target_id and not is_admin and user.id not in ADMIN_IDS:
            await query.answer("هذا الزر مخصص للعضو الجديد فقط!", show_alert=True)
            return
        
        self.db.save_user(user)
        self.db.set_role(target_id, role)
        await query.message.reply_text(role_text, parse_mode=ParseMode.HTML)
    
    async def show_rules(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)
    
    async def handle_message(self, update, context):
        message = update.message
        user = update.effective_user
        
        if not message or not user:
            return
        
        self.db.save_user(user)
        text = message.text or ""
        if not text:
            return
        
        normalized_text = self.normalize_text(text).strip()
        
        if normalized_text in ["انا كابتن", "انا سايق", "انا سواق"]:
            self.db.save_user(user)
            self.db.set_role(user.id, "driver")
            await message.reply_text("✅ <b>تم تسجيلك ككابتن!</b>", parse_mode=ParseMode.HTML)
            return
        
        if normalized_text in ["انا عميل", "انا زبون", "انا طالب"]:
            self.db.save_user(user)
            self.db.set_role(user.id, "customer")
            await message.reply_text("✅ <b>تم تسجيلك كعميل!</b>", parse_mode=ParseMode.HTML)
            return
        
        if self.looks_like_trip(text):
            await self.handle_trip_request(update, context, text)
            return
        
        chat_response = self.get_chat_response(text)
        if chat_response:
            await message.reply_text(chat_response)
            return
        
        greeting = self.get_greeting(text)
        if greeting:
            await message.reply_text(greeting)
            return
    
    async def handle_trip_request(self, update, context, text):
        message = update.message
        user = update.effective_user
        
        pickup, destination = self.extract_route(text)
        
        if not pickup or not destination:
            pickup = "غير محدد"
            destination = "غير محدد"
        
        trip_type = self.detect_trip_type(text) or "normal"
        
        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            pickup=pickup,
            destination=destination,
            trip_type=trip_type
        )
        
        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        
        confirm_text = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>نوع المشوار:</b> {type_badge}

🚕 <b>للكباتن:</b>
اضغطوا الزر بالأسفل 👇

📝 <b>تفاصيل الطلب:</b>
{self.html(text)}
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}"),
            ],
        ])
        
        await message.reply_text(confirm_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    async def handle_take_trip(self, update, context):
        query = update.callback_query
        driver = query.from_user
        data = query.data.split(":")
        trip_id = int(data[1])
        customer_id = int(data[2])
        
        if driver.id == customer_id:
            await query.answer("😂 ما تقدر تأخذ مشوارك بنفسك!", show_alert=True)
            return
        
        self.db.save_user(driver)
        
        if not self.db.is_driver(driver.id):
            self.db.set_role(driver.id, "driver")
        
        added = self.db.add_ready_driver(trip_id, driver.id)
        
        if not added:
            await query.answer("✅ أنت مسجل جاهز لهذا المشوار بالفعل!", show_alert=True)
            return
        
        trip = self.db.get_trip(trip_id)
        
        if not trip:
            await query.answer("⚠️ المشوار غير موجود!", show_alert=True)
            return
        
        type_badge = "🔄 شهري" if trip["trip_type"] == "monthly" else "🚗 عادي"
        
        card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}

📋 <b>نوع المشوار:</b> {type_badge}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}

💰 <b>السعر:</b> بالتفاهم بالخاص
        """
        
        contact_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📩 تواصل مع العميل", callback_data=f"contact_customer:{trip_id}:{driver.id}"),
            ],
            [
                InlineKeyboardButton("🚕 تواصل مع الكابتن", callback_data=f"contact_driver:{trip_id}:{driver.id}"),
            ],
        ])
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=card_text,
            parse_mode=ParseMode.HTML,
            reply_markup=contact_keyboard
        )
        
        await query.answer("✅ تم تسجيلك للمشوار!", show_alert=True)
    
    async def contact_customer(self, update, context):
        query = update.callback_query
        user = query.from_user
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        if user.id != driver_id:
            await query.answer("هذا الزر مخصص للكابتن!", show_alert=True)
            return
        
        trip = self.db.get_trip(trip_id)
        
        if trip:
            await query.answer("📩 فتح تواصل العميل...", url=f"tg://user?id={trip['customer_id']}")
    
    async def contact_driver(self, update, context):
        query = update.callback_query
        user = query.from_user
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        trip = self.db.get_trip(trip_id)
        
        if not trip or trip["customer_id"] != user.id:
            await query.answer("هذا الزر مخصص لصاحب الطلب!", show_alert=True)
            return
        
        await query.answer("🚕 فتح تواصل الكابتن...", url=f"tg://user?id={driver_id}")
    
    async def cmd_start(self, update, context):
        await update.message.reply_text(
            f"🚘 <b>{GROUP_NAME}</b>\n\n🤖 البوت يعمل ✅",
            parse_mode=ParseMode.HTML
        )
    
    async def cmd_rules(self, update, context):
        await update.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)
    
    async def cmd_help(self, update, context):
        await update.message.reply_text(
            "👤 <b>عميل:</b> اكتب طلبك\n"
            "🚕 <b>كابتن:</b> اضغط زر «أنا جاهز»",
            parse_mode=ParseMode.HTML
        )
    
    async def smart_reminder(self, context):
        current_hour = datetime.now(SAUDI_TZ).hour
        if 2 <= current_hour < 8:
            return
        text = random.choice(ENGAGEMENT_MESSAGES)
        try:
            await context.bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML)
        except:
            pass
    
    def run(self):
        app = Application.builder().token(TOKEN).build()
        
        app.job_queue.run_repeating(self.smart_reminder, interval=ENGAGEMENT_INTERVAL, first=60)
        
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.welcome_new_member))
        
        app.add_handler(CallbackQueryHandler(self.role_selection, pattern="^role_"))
        app.add_handler(CallbackQueryHandler(self.show_rules, pattern="^rules$"))
        app.add_handler(CallbackQueryHandler(self.handle_take_trip, pattern="^take_trip:"))
        app.add_handler(CallbackQueryHandler(self.contact_customer, pattern="^contact_customer:"))
        app.add_handler(CallbackQueryHandler(self.contact_driver, pattern="^contact_driver:"))
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("✅ البوت يعمل...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

# ============================================================
# 🚀 نقطة البداية
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("✅ تم حذف قاعدة البيانات القديمة")
    
    bot = SmartRidesBot()
    bot.run()
