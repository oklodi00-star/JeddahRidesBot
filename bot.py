"""
🤖 بوت مشاوير جدة الذكي - مسموح برسالة تواجد واحدة ثم تنبيه/تجاهل للتكرار
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

TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROUP_ID = -1001234567890
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]

ALLOWED_GROUP_LINK = "https://t.me/JeddahRidesGroup"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب مخصص للمشاوير والنقل فقط.
2️⃣ يكتب العميل طلبه مباشرة.
3️⃣ 🚕 يضغط الكابتن على زر «أنا جاهز للمشوار» تحت الطلب.
4️⃣ 💰 يتم التفاهم على السعر بالخاص.
5️⃣ 🚫 يمنع الإعلان أو إرسال الروابط الخارجية منعاً باتاً.
6️⃣ 🤝 الاحترام المتبادل واجب بين الجميع.

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

WELCOME_TEXT = f"""
🎉 <b>أهلاً بك في {GROUP_NAME}!</b>

نحن هنا لتسهيل تنقلاتكم داخل جدة بكل سرعة وأمان. 🚗💨

📌 <b>طريقة طلب مشوار:</b>
فقط اكتب تفاصيل طلبك مباشرة في القروب (مثال: <i>من الفضيلة إلى الرغامة</i>)، وسيقوم البوت بتسجيل طلبك فوراً ليظهر للكباتن!

اختر حالتك أو تصفح القسم الذي يناسبك عبر الأزرار أدناه 👇
"""

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
    "الفلاح", "النهضة", "الرابية", "الخزامى", "السلام مول", "السلام", "مجمع الشرق"
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

    def add_memory(self, user_id, text):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO user_memory (user_id, message_text) VALUES (?, ?)", (user_id, text))
        self.conn.commit()

    def is_spam(self, user_id, text, within_seconds=300):
        # منع تكرار نفس الرسالة لفترة معينة (مثال: 5 دقائق لتجنب الإزعاج المتكرر)
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
# 🤖 آليات المعالجة والذكاء
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

    def contains_unauthorized_links(self, text, message_entities):
        if not text:
            return False

        if message_entities:
            for entity in message_entities:
                if entity.type in ["url", "text_link"]:
                    url_val = entity.url if entity.type == "text_link" else text[entity.offset:entity.offset + entity.length]
                    if url_val and url_val.strip().lower() != ALLOWED_GROUP_LINK.lower():
                        return True

        url_pattern = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*))"
        found_urls = re.findall(url_pattern, text)
        
        for u in found_urls:
            clean_u = u.strip()
            if clean_u.lower() != ALLOWED_GROUP_LINK.lower() and not clean_u.endswith(ALLOWED_GROUP_LINK.lower()):
                return True

        return False

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
            return locations[0], locations[1]
        
        return "موقع البداية", "الوجهة المطلوبة"

    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚕 أنا كابتن", callback_data="btn_driver"),
                    InlineKeyboardButton("👤 أنا عميل", callback_data="btn_customer")
                ],
                [
                    InlineKeyboardButton("⚠️ الشكاوي", url=f"https://t.me/{ADMIN_USERNAME}"),
                    InlineKeyboardButton("📋 القوانين", callback_data="btn_rules")
                ]
            ])

            await update.message.reply_text(
                f"مرحباً بك {member.first_name} في قروب {GROUP_NAME}!\n\n" + WELCOME_TEXT,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

    async def handle_callback_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data

        if data == "btn_driver":
            self.db.set_role(query.from_user.id, "driver")
            await query.answer("✅ تم تسجيلك ككابتن بنجاح في النظام!", show_alert=True)
        elif data == "btn_customer":
            self.db.set_role(query.from_user.id, "customer")
            await query.answer("✅ تم تسجيلك كعميل بنجاح في النظام!", show_alert=True)
        elif data == "btn_rules":
            await query.answer()
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=RULES_TEXT,
                parse_mode=ParseMode.HTML
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user = update.effective_user
        if not message or not user:
            return

        self.db.save_user(user)

        if self.db.is_banned(user.id):
            return

        text = message.text or message.caption or ""
        entities = message.entities or message.caption_entities or []

        if self.contains_unauthorized_links(text, entities):
            try:
                await message.delete()
            except Exception:
                pass
            
            warning_msg = await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"⚠️ عذراً يا {user.first_name}، ممنوع إرسال الروابط أو الإعلانات الخارجية في القروب. يُسمح فقط برابط القروب الرسمي."
            )
            context.job_queue.run_once(lambda ctx: ctx.bot.delete_message(chat_id=message.chat_id, message_id=warning_msg.message_id), 6)
            return

        if not text:
            return

        norm = self.normalize_text(text).strip()

        # فحص التكرار (مسموح بالمرة الأولى، وإذا تكررت خلال الفترة المحددة يتم تنبيهه أو تجاهلها)
        if any(w in norm for w in PRESENCE_WORDS):
            if self.db.is_spam(user.id, norm):
                warning_msg = await message.reply_text(f"⚠️ تنبيه يا {user.first_name}، لقد أرسلت حالة تواجدك مسبقاً. يرجى عدم تكرار نفس الرسالة باستمرار.")
                context.job_queue.run_once(lambda ctx: ctx.bot.delete_message(chat_id=message.chat_id, message_id=warning_msg.message_id), 6)
                return
            
            self.db.add_spam_record(user.id, norm)
            self.db.set_role(user.id, "driver")
            await message.reply_text("✅ تم تسجيل تواجدك.")
            return

        if self.db.is_spam(user.id, text):
            return
        self.db.add_spam_record(user.id, text)
        self.db.add_memory(user.id, text)

        if self.looks_like_trip(text):
            await self.handle_trip(update, context, text)
            return

        if norm in ["انا كابتن", "كابتن", "سايق", "سواق"]:
            self.db.set_role(user.id, "driver")
            await message.reply_text("✅ تم تسجيلك ككابتن بنجاح!")
            return

        if norm in ["انا عميل", "عميل", "زبون"]:
            self.db.set_role(user.id, "customer")
            await message.reply_text("✅ تم تسجيلك كعميل بنجاح!\nيمكنك الآن إرسال تفاصيل مشوارك.")
            return

        if any(g == norm or norm.startswith(g + " ") for g in GREETINGS):
            await message.reply_text("وعليكم السلام ورحمة الله! 😊 أهلاً بك في مشاوير جدة، اكتب تفاصيل مشوارك وسأقوم بتسجيله فوراً.")
            return

        await message.reply_text("❓ عذراً، لم أفهم طلبك. اكتب طلب المشوار مباشرة (مثلاً: من الفضيلة إلى الرغامة).")

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

        customer_chat_url = f"tg://user?id={trip['customer_id']}"
        driver_chat_url = f"tg://user?id={driver.id}"

        card_text = f"""
⚡️ <b>ZOOM</b> ⚡️
تم تأكيد كابتن جاهز للمشوار!

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 تواصل مع العميل", url=customer_chat_url)],
            [InlineKeyboardButton("🚕 تواصل مع الكابتن", url=driver_chat_url)]
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

def main():
    if not TOKEN:
        print("❌ تنبيه: يرجى التأكد من وضع توكن البوت في المتغيرات.")
        return

    application = Application.builder().token(TOKEN).build()
    bot_instance = SmartRidesBot()

    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text(f"🚘 أهلاً بك في {GROUP_NAME}\nالبوت يعمل بكفاءة عالية.")))
    application.add_handler(CommandHandler("rules", lambda u, c: u.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_instance.handle_new_member))
    
    application.add_handler(CallbackQueryHandler(bot_instance.handle_take_trip, pattern=r"^take_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.close_trip, pattern=r"^close_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_callback_buttons, pattern=r"^btn_"))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message))

    print("✅ تم تشغيل بوت مشاوير جدة بنجاح وتفعيل نظام التواحد لمرة واحدة ثم التحذير...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
