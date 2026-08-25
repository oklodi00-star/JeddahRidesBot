"""
🤖 بوت مشاوير جدة الذكي - النسخة المطورة
"""

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

TOKEN = "8881485708:AAFfqmYZ4QmLEqBF28ATOtDWYa6o2GVn2F4"

GROUP_ID = -1001234567890  # ⚠️ ضع ايدي القروب هنا
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

OWNER_ID = 952638746
ADMIN_USERNAME = "klodi500"
ADMIN_USERNAMES = ["klodi500"]
ADMIN_IDS = [952638746]

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides.db"

DRIVER_BADGE = "𓆩🚘𓆪 كابتن"
CUSTOMER_BADGE = "𓆩👤𓆪 عميل"

REMINDER_INTERVAL = 30 * 60
MUTE_HOURS = 24
VIOLATION_RESET_DAYS = 30

# ============================================================
# 📋 قانون القروب
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه مباشرة:
📍 من وين → إلى وين

3️⃣ 🚕 الكابتن إذا يبي المشوار:
↩️ يقتبس رسالة العميل ويكتب «جاهز»

4️⃣ 💰 السعر والتفاهم بين العميل والكابتن بالخاص.

5️⃣ 🚫 ممنوع كتابة «خاص» داخل القروب.

6️⃣ 🚫 يمنع السب والإساءة.

7️⃣ 🚫 يمنع نشر الإعلانات والروابط.

8️⃣ 🔄 الرسائل المحولة ممنوعة.

9️⃣ 📍 الكابتن يعلن موقعه مرة واحدة يوميًا.

🔟 🤝 الاحترام واجب على الجميع.

⚠️ <b>نظام المخالفات:</b>
🟡 الأولى → تحذير
🟠 الثانية → تحذير
🔴 الثالثة → تحذير أخير
🔇 الرابعة → كتم 24 ساعة

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🤖 كلمات ذكية
# ============================================================

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني",
    "ابغى اروح", "ابي اروح", "ابغا اروح",
    "ابغى مشوار", "ابي مشوار", "ابغا مشوار",
    "احتاج مشوار", "محتاج مشوار", "احتاج توصيل",
    "احد يوصلني", "مين يوصلني", "من يوصلني",
]

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "يومياً",
    "اسبوعي", "اسبوعيا", "أسبوعي", "أسبوعياً",
    "دوام", "مدرسة", "جامعة", "عمل", "شغل",
    "مشوار يومي", "توصيل يومي", "مشوار شهري",
]

DRIVER_READY_PHRASES = [
    "جاهز", "جاهز للمشوار", "جاهز للمشاوير",
    "كابتن وجاهز", "كابتن جاهز", "انا كابتن",
    "انا كابتن وجاهز", "جاهز لاي مشوار",
    "جاهز لأي مشوار", "متوفر للمشاوير",
    "متوفر لاي مشوار", "متوفر لأي مشوار",
]

GREETINGS = [
    (
        ["السلام عليكم", "سلام عليكم", "السلام عليكم ورحمة الله"],
        ["وعليكم السلام ورحمة الله وبركاته 🌹🚘", "وعليكم السلام يا هلا والله 👋", "وعليكم السلام، نورت القروب 🌹🚘"],
    ),
    (
        ["هلا", "هلا والله", "هلا وغلا", "يا هلا", "اهلا", "اهلين", "مرحبا"],
        ["هلا وغلا 🌹🚘", "يا هلا والله 👋", "حياك الله ونورتنا 🌹"],
    ),
    (
        ["صباح الخير", "صباحكم خير"],
        ["صباح النور والرزق 🌹🚘", "صباحكم خير وبركة 🤲", "صباح الخير يا أهل المشاوير ☀️"],
    ),
    (
        ["مساء الخير", "مساءكم خير"],
        ["مساء النور والخير 🌙🌹", "الله يمسيكم بالخير والعافية 🚘", "مساءكم طيب يا جماعة الخير ❤️"],
    ),
    (
        ["شكرا", "مشكور", "يعطيك العافيه", "الله يعطيك العافيه"],
        ["العفو يا الغالي 🌹", "حاضرين وما سوينا إلا الواجب 🚘", "الله يعافيك ويسعدك ❤️"],
    ),
]

READY_MESSAGES = [
    "رافقتك السلامة يا كابتن 🚕🌹",
    "الله يوفقك ويرزقك مشوار طيب 🤲🚘",
    "على بركة الله يا كابتن، رافقتك السلامة 🌹",
    "الله يرزقك ويرزق العميل، مشوار موفق 🚕✨",
    "بيض الله وجهك يا كابتن، الله يوفقك 🤲",
    "تم تسجيل جاهزيتك، رزقك الله بالمشوار الطيب 🚘🌹",
]

BAD_WORDS = [
    "يا غبي", "يا حمار", "يا كلب", "يا تافه",
    "قليل الادب", "قليل الأدب", "انقلع",
]

INAPPROPRIATE = [
    "مين يبي يتعرف", "مين يبغى يتعرف",
    "ابغى بنت", "ابغى وحدة", "تعالي معي",
]

LOCATION_PHRASES = [
    "متواجد في", "متواجد ب", "موجود في", "موجود ب",
    "انا في", "انا موجود في", "متوفر في", "متوفر ب",
    "متواجد حاليا في", "موجود حاليا في",
]

REMINDERS = [
    "🚘🔥 <b>يا كباتن وعملاء {GROUP_NAME}!</b>\n\nخلونا نزيد التفاعل ونوصل القروب لأكبر عدد 🙌\n📢 انشر رابط القروب للي يحتاج مشاوير.\n\n🔗 {GROUP_LINK}",
    "📣 <b>تذكير سريع يا أهل المشاوير ❤️</b>\n\nعندك صاحب يحتاج مشاوير؟\nأرسل له رابط القروب وخله ينضم 🚘🔥\n\n🔗 {GROUP_LINK}",
    "🚕 <b>كباتننا وينكم؟ 😎🔥</b>\n🧑🏻‍💼 <b>وعملائنا وينكم؟ ❤️</b>\n\nخلونا نكبر القروب ونزيد الطلبات.\n\n🔗 {GROUP_LINK}",
]

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
                    violations INTEGER DEFAULT 0,
                    last_violation_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS driver_locations (
                    driver_id INTEGER PRIMARY KEY,
                    last_date TEXT
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
    
    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal"):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips 
                (message_id, customer_id, pickup, destination, trip_type)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type))
            con.commit()
    
    def get_trip_by_message(self, message_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE message_id = ?", (message_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id)
                VALUES (?, ?)
            """, (trip_id, driver_id))
            con.commit()
            return cur.rowcount > 0
    
    def is_driver_ready(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM ready_drivers WHERE trip_id = ? AND driver_id = ?", (trip_id, driver_id))
            return cur.fetchone() is not None
    
    def add_violation(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT violations, last_violation_at FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            
            current = row[0] if row else 0
            last_at = row[1] if row else None
            
            if last_at:
                try:
                    last_dt = datetime.fromisoformat(last_at)
                    if (datetime.now(SAUDI_TZ) - last_dt).days >= VIOLATION_RESET_DAYS:
                        current = 0
                except:
                    pass
            
            count = current + 1
            
            cur.execute("""
                UPDATE users SET violations = ?, last_violation_at = ?
                WHERE user_id = ?
            """, (count, datetime.now(SAUDI_TZ).isoformat(), user_id))
            con.commit()
            
            return count
    
    def check_location_today(self, driver_id):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT last_date FROM driver_locations WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            
            if row and row[0] == today:
                return True
            
            cur.execute("""
                INSERT OR REPLACE INTO driver_locations (driver_id, last_date)
                VALUES (?, ?)
            """, (driver_id, today))
            con.commit()
            return False

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
    
    def extract_route(self, text):
        match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        if "→" in text or "->" in text:
            parts = re.split(r"→|->", text)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
        
        return None, None
    
    def looks_like_trip(self, text):
        return self.detect_trip_type(text) is not None
    
    def is_ready_reply(self, text):
        normalized = self.normalize_text(text).strip()
        return normalized in [self.normalize_text(p) for p in DRIVER_READY_PHRASES]
    
    def looks_like_location(self, text):
        normalized = self.normalize_text(text)
        return any(self.normalize_text(p) in normalized for p in LOCATION_PHRASES)
    
    def get_greeting(self, text):
        normalized = self.normalize_text(text)
        for phrases, responses in GREETINGS:
            for phrase in phrases:
                if normalized.startswith(self.normalize_text(phrase)):
                    return random.choice(responses)
        return None
    
    def violation_reason(self, text):
        normalized = self.normalize_text(text).strip()
        
        if normalized in ["خاص", "الخاص"]:
            return "خاص"
        
        for word in BAD_WORDS:
            if self.normalize_text(word) in normalized:
                return "إساءة"
        
        for phrase in INAPPROPRIATE:
            if self.normalize_text(phrase) in normalized:
                return "كلام غير مناسب"
        
        return None
    
    def is_forwarded(self, message):
        return bool(
            getattr(message, "forward_origin", None) or
            getattr(message, "forward_from", None) or
            getattr(message, "forward_from_chat", None) or
            getattr(message, "forward_sender_name", None)
        )
    
    def forbidden_link(self, text):
        if not text:
            return False
        
        url_pattern = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)", re.IGNORECASE)
        
        for link in url_pattern.findall(text):
            link = link.rstrip(".,!?؟،؛:)]}>\"'")
            normalized = link.lower().rstrip("/")
            
            if normalized.startswith(GROUP_LINK.lower().rstrip("/")):
                continue
            
            if any(domain in normalized for domain in ["maps.google.com", "goo.gl/maps", "maps.app.goo.gl"]):
                continue
            
            return True
        
        return False
    
    async def is_admin(self, update, context):
        user = update.effective_user
        if not user:
            return False
        
        if user.id in ADMIN_IDS:
            return True
        
        if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
            return True
        
        try:
            member = await context.bot.get_chat_member(GROUP_ID, user.id)
            return member.status in ["administrator", "creator"]
        except:
            return False
    
    def get_role_badge(self, user_id):
        if self.db.is_driver(user_id):
            return DRIVER_BADGE
        if self.db.is_customer(user_id):
            return CUSTOMER_BADGE
        return ""
    
    def display_user(self, user):
        if not user:
            return "عضو"
        name = self.html(user.full_name)
        badge = self.get_role_badge(user.id)
        if badge:
            return f"<b>{self.html(badge)} {name}</b>"
        return f"<b>{name}</b>"
    
    async def welcome_new_member(self, update, context):
        message = update.message
        
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            
            self.db.save_user(member)
            
            welcome_text = f"""
🌟 <b>يا هلا {self.html(member.full_name)}!</b>

نورت <b>{GROUP_NAME}</b> 🚘

━━━━━━━━━━━━━━━━

👤 <b>إذا أنت عميل:</b>
اكتب طلبك مباشرة مثل:
«مشوار من الفضيلة إلى الرغامة»

🚕 <b>إذا أنت كابتن:</b>
إذا شفت طلب يناسبك:
↩️ <b>اقتبس رسالة العميل</b> واكتب «جاهز»

━━━━━━━━━━━━━━━━

⚠️ <b>مهم:</b>
الكابتن لازم يكتب «جاهز» على طلب العميل عشان يتواصل معه

اختر دورك:
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
    
    async def member_left(self, update, context):
        message = update.message
        left_member = message.left_chat_member
        
        if left_member.is_bot:
            return
        
        self.db.save_user(left_member)
        
        badge = self.get_role_badge(left_member.id)
        badge_text = f"\n🏷️ <b>الصفة:</b> {self.html(badge)}" if badge else ""
        
        username_text = f"\n🔹 <b>اليوزر:</b> @{self.html(left_member.username)}" if left_member.username else ""
        
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""
🚨 <b>تنبيه مغادرة عضو</b>

👤 <b>الاسم:</b> {self.html(left_member.full_name)}
{username_text}
{badge_text}

🆔 <b>ID:</b> <code>{left_member.id}</code>
👋 غادر القروب
📍 <b>القروب:</b> {self.html(GROUP_NAME)}
                """,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error sending left notification: {e}")
    
    async def role_selection(self, update, context):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        if data.startswith("role_customer:"):
            role = "customer"
        elif data.startswith("role_driver:"):
            role = "driver"
        else:
            return
        
        target_id = int(data.split(":")[1])
        
        if user.id != target_id and not await self.is_admin(update, context):
            await query.answer("هذا الزر مخصص للعضو الجديد فقط!", show_alert=True)
            return
        
        self.db.save_user(user)
        self.db.set_role(target_id, role)
        
        if role == "customer":
            confirm_text = f"""
✅ <b>تم تسجيلك كعميل!</b>

👤 <b>طريقة طلب المشوار:</b>
اكتب طلبك مباشرة في القروب

📝 <b>مثال:</b>
«مشوار من الفضيلة إلى الرغامة»

🤖 البوت بيفهم طلبك تلقائياً
            """
        else:
            confirm_text = f"""
✅ <b>تم تسجيلك ككابتن!</b>

🚕 <b>طريقة قبول المشوار:</b>
إذا شفت طلب يناسبك:
↩️ <b>اقتبس رسالة العميل</b> واكتب «جاهز»

🤖 البوت بيرسل لك كرت التواصل مع العميل

📍 <b>أعلن موقعك مرة يومياً:</b>
اكتب «موجود في الحمدانية لأي مشوار»
            """
        
        await query.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
    
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
        
        if self.is_forwarded(message) and not await self.is_admin(update, context):
            try:
                await message.delete()
            except:
                pass
            await message.reply_text(f"⚠️ {self.display_user(user)}\n\nالرسائل المحولة ممنوعة 🚫", parse_mode=ParseMode.HTML)
            return
        
        if self.forbidden_link(text) and not await self.is_admin(update, context):
            try:
                await message.delete()
            except:
                pass
            await message.reply_text(f"⚠️ {self.display_user(user)}\n\nالروابط ممنوعة 🚫\n📍 روابط Google Maps مسموحة فقط", parse_mode=ParseMode.HTML)
            return
        
        reason = self.violation_reason(text)
        if reason and not await self.is_admin(update, context):
            await self.handle_violation(update, context, reason)
            return
        
        if self.is_ready_reply(text):
            await self.handle_ready_reply(update, context)
            return
        
        if self.looks_like_trip(text):
            await self.handle_trip_request(update, context, text)
            return
        
        if self.looks_like_location(text):
            await self.handle_location(update, context, text)
            return
        
        greeting = self.get_greeting(text)
        if greeting and not self.looks_like_trip(text):
            await message.reply_text(greeting)
            return
    
    async def handle_trip_request(self, update, context, text):
        message = update.message
        user = update.effective_user
        
        pickup, destination = self.extract_route(text)
        
        if not pickup or not destination:
            return
        
        trip_type = self.detect_trip_type(text)
        
        self.db.create_trip(
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
📍 <b>من:</b> {self.html(pickup)}
🎯 <b>إلى:</b> {self.html(destination)}

🚕 <b>للكباتن:</b>
اقتبسوا هذه الرسالة واكتبوا «جاهز»
        """
        
        await message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
    
    async def handle_ready_reply(self, update, context):
        message = update.message
        driver = update.effective_user
        
        if not message.reply_to_message:
            await message.reply_text(
                "⚠️ <b>تنبيه!</b>\n\nلأخذ مشوار، لازم <b>تقتبس رسالة العميل</b> وترد عليها بكلمة «جاهز»",
                parse_mode=ParseMode.HTML
            )
            return
        
        replied_message = message.reply_to_message
        
        trip = self.db.get_trip_by_message(replied_message.message_id)
        
        if not trip:
            await message.reply_text(
                "⚠️ هذه ليست رسالة طلب مشوار!\nرد على رسالة العميل الأصلية",
                parse_mode=ParseMode.HTML
            )
            return
        
        if trip["customer_id"] == driver.id:
            await message.reply_text("😂 ما تقدر تأخذ مشوارك بنفسك!", parse_mode=ParseMode.HTML)
            return
        
        self.db.save_user(driver)
        
        if not self.db.is_driver(driver.id):
            self.db.set_role(driver.id, "driver")
        
        added = self.db.add_ready_driver(trip["trip_id"], driver.id)
        
        if not added:
            await message.reply_text("✅ أنت مسجل جاهز لهذا المشوار بالفعل!", parse_mode=ParseMode.HTML)
            return
        
        type_badge = "🔄 شهري" if trip["trip_type"] == "monthly" else "🚗 عادي"
        
        card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}

📋 <b>نوع المشوار:</b> {type_badge}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}

💰 <b>السعر والتفاهم بالخاص</b>

━━━━━━━━━━━━━━━━
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📩 التواصل مع العميل", callback_data=f"contact_customer:{trip['trip_id']}:{driver.id}"),
            ],
            [
                InlineKeyboardButton("🚕 التواصل مع الكابتن", callback_data=f"contact_driver:{trip['trip_id']}:{driver.id}"),
            ],
        ])
        
        await message.reply_text(card_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        await message.reply_text(random.choice(READY_MESSAGES), parse_mode=ParseMode.HTML)
    
    async def handle_location(self, update, context, text):
        message = update.message
        driver = update.effective_user
        
        if not self.db.is_driver(driver.id):
            await message.reply_text(
                "📍 هذا الإعلان مخصص للكباتن فقط 🚕\n\n"
                "إذا أنت كابتن اضغط «🚕 أنا كابتن» مرة واحدة",
                parse_mode=ParseMode.HTML
            )
            return
        
        already_posted = self.db.check_location_today(driver.id)
        
        if already_posted:
            await message.reply_text(
                "😂 عرفنا وينك اليوم.\n\n📍 إعلان التواجد مسموح مرة واحدة فقط باليوم",
                parse_mode=ParseMode.HTML
            )
            return
        
        await message.reply_text(
            f"📍 <b>تم تسجيل تواجد الكابتن</b>\n\n"
            f"{self.display_user(driver)}\n\n"
            f"📌 {self.html(text)}\n\n"
            f"🚕 تم تسجيل موقعك، الله يرزقك مشوار طيب",
            parse_mode=ParseMode.HTML
        )
    
    async def handle_violation(self, update, context, reason):
        message = update.message
        user = update.effective_user
        
        try:
            await message.delete()
        except:
            pass
        
        count = self.db.add_violation(user.id)
        
        if reason == "خاص":
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⚠️ {self.display_user(user)}\n\n🚫 ممنوع كتابة «خاص»\n📝 تم تسجيلها كمخالفة",
                parse_mode=ParseMode.HTML
            )
        
        if count >= 4:
            try:
                until = datetime.now(SAUDI_TZ) + timedelta(hours=MUTE_HOURS)
                await context.bot.restrict_chat_member(
                    GROUP_ID, user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                await context.bot.send_message(
                    GROUP_ID,
                    f"🔇 <b>تم كتم العضو</b>\n\n{self.display_user(user)}\n\n🔴 المخالفة رقم <b>{count}</b>\n⏱ مدة الكتم: <b>24 ساعة</b>",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Mute error: {e}")
        
        elif count == 3:
            await context.bot.send_message(
                GROUP_ID,
                f"🔴 <b>المخالفة الثالثة</b>\n\n{self.display_user(user)}\n\n⚠️ هذه آخر مخالفة قبل الكتم",
                parse_mode=ParseMode.HTML
            )
        
        elif count == 2:
            await context.bot.send_message(
                GROUP_ID,
                f"🟠 <b>المخالفة الثانية</b>\n\n{self.display_user(user)}\n\nالسبب: {self.html(reason)}",
                parse_mode=ParseMode.HTML
            )
        
        else:
            await context.bot.send_message(
                GROUP_ID,
                f"🟡 <b>تنبيه للمرة الأولى</b>\n\n{self.display_user(user)}\n\nالسبب: {self.html(reason)}",
                parse_mode=ParseMode.HTML
            )
    
    async def contact_customer(self, update, context):
        query = update.callback_query
        user = query.from_user
        
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        if user.id != driver_id:
            await query.answer("هذا الزر مخصص للكابتن المسجل!", show_alert=True)
            return
        
        if not self.db.is_driver_ready(trip_id, driver_id):
            await query.answer("أنت غير مسجل لهذا المشوار!", show_alert=True)
            return
        
        trip = self.db.get_trip_by_message(trip_id)
        customer_id = trip["customer_id"]
        
        await query.answer("📩 فتح تواصل العميل...", url=f"tg://user?id={customer_id}")
    
    async def contact_driver(self, update, context):
        query = update.callback_query
        user = query.from_user
        
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        trip = self.db.get_trip_by_message(trip_id)
        
        if not trip or trip["customer_id"] != user.id:
            await query.answer("هذا الزر مخصص لصاحب الطلب فقط!", show_alert=True)
            return
        
        await query.answer("🚕 فتح تواصل الكابتن...", url=f"tg://user?id={driver_id}")
    
    async def cmd_start(self, update, context):
        await update.message.reply_text(
            f"🚘 <b>أهلاً بك في {GROUP_NAME}</b>\n\n"
            "🤖 البوت يعمل بنجاح ✅\n\n"
            "📋 /rules - القوانين\nℹ️ /help - المساعدة",
            parse_mode=ParseMode.HTML
        )
    
    async def cmd_rules(self, update, context):
        await update.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)
    
    async def cmd_help(self, update, context):
        help_text = f"""
🤖 <b>طريقة استخدام البوت</b>

👤 <b>للعميل:</b>
اكتب مشوارك مباشرة:
«مشوار من الفضيلة إلى الرغامة»

🚕 <b>للكابتن:</b>
اقتبس رسالة العميل واكتب «جاهز»

📋 <b>أنواع المشاوير:</b>
• 🚗 عادي: توصيلة واحدة
• 🔄 شهري: دوام، مدرسة، جامعة

📍 <b>إعلان الموقع:</b>
اكتب «موجود في الحمدانية لأي مشوار»

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def smart_reminder(self, context):
        current_hour = datetime.now(SAUDI_TZ).hour
        
        if 2 <= current_hour < 8:
            return
        
        text = random.choice(REMINDERS).format(
            GROUP_NAME=GROUP_NAME,
            GROUP_LINK=GROUP_LINK
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📤 نشر رابط القروب", url=f"https://t.me/share/url?url={GROUP_LINK}&text=🚘 انضموا لقروب مشاوير جدة"),
            ],
            [
                InlineKeyboardButton("🚘 فتح القروب", url=GROUP_LINK),
            ],
        ])
        
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Reminder error: {e}")
    
    def run(self):
        app = Application.builder().token(TOKEN).build()
        
        app.job_queue.run_repeating(
            self.smart_reminder,
            interval=REMINDER_INTERVAL,
            first=REMINDER_INTERVAL
        )
        
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.welcome_new_member))
        app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.member_left))
        
        app.add_handler(CallbackQueryHandler(self.role_selection, pattern="^role_"))
        app.add_handler(CallbackQueryHandler(self.show_rules, pattern="^rules$"))
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
    
    bot = SmartRidesBot()
    bot.run()
