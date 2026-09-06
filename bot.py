"""
🤖 بوت مشاوير جدة الذكي
- العميل يرسل طلبه مباشرة بدون تسجيل مسبق
- الكابتن يضغط جاهز مباشرة بدون تسجيل مسبق
- زر التواصل يفتح الخاص مباشرة بين العميل والكابتن
- منع كلمة "خاص"
- منع أرقام الجوال
- 3 مخالفات = كتم 24 ساعة
- تسجيل تواجد الكابتن مرة واحدة يومياً
- تكرار التواجد = مخالفة
"""

import os
import re
import logging
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
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

# إعداد السجل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()

GROUP_ID = -1001234567890  # استبدل هذا بآيدي القروب الحقيقي الصحيح
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"

ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]

ALLOWED_GROUP_LINK = "https://t.me/JeddahRidesGroup"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides.db"


# ============================================================
# 📋 القوانين والترحيب
# ============================================================

WELCOME_TEXT = f"""
🎉 <b>أهلاً وسهلاً بك في {GROUP_NAME}</b>

🚘 المجموعة مخصصة للمشاوير داخل جدة وضواحيها.

━━━━━━━━━━━━━━━━━━

👤 <b>طريقة طلب مشوار للعميل:</b>
اكتب طلبك مباشرة في القروب، مثلاً:
«من الفضيلة إلى الأندلس الساعة 5 مساءً»

🤖 سيقوم البوت بتسجيل طلبك وإنشاء بطاقة للمشوار.

━━━━━━━━━━━━━━━━━━

🚕 <b>طريقة الكابتن:</b>
إذا كنت جاهزاً لتنفيذ أحد الطلبات:
اضغط زر «🚕 جاهز» أو اقتبس طلب العميل واكتب «جاهز».

━━━━━━━━━━━━━━━━━━

📍 <b>إعلان التواجد:</b>
مثلاً: «متواجد في الفضيلة»
⚠️ يسمح بتسجيل التواجد مرة واحدة يومياً.

━━━━━━━━━━━━━━━━━━

🚫 <b>مهم:</b>
ممنوع كتابة «خاص».
ممنوع نشر أرقام الجوال.
التواصل يكون عن طريق أزرار البوت فقط.
"""


# ============================================================
# 📚 الكلمات المفتاحية
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "شهريه", "شهرياً", "شهريا", "بالشهر", "دوام", 
    "مدرسه", "مدرسة", "جامعه", "جامعة", "التزام", "اسبوعي", 
    "أسبوعي", "يومي", "يوميا", "يومياً", "مشوار يومي", "توصيل يومي"
]

NORMAL_TRIP_WORDS = [
    "مشوار", "مشاوير", "توصيل", "توصيله", "توصيلة", "يوصلني", 
    "يوديني", "ابغى مشوار", "ابي مشوار", "أبي مشوار", "ابغا مشوار", 
    "أبغا مشوار", "احتاج توصيل", "أحتاج توصيل", "محتاج توصيل", 
    "محتاجة توصيل", "من يوصلني", "اوصلني", "أوصلني", "ودني", "خذني", 
    "ابي اروح", "أبي أروح", "ابغى اروح", "أبغى أروح", "ابغا اروح", "اريد مشوار"
]

PRESENCE_WORDS = [
    "متواجد", "متواجده", "متواجدة", "موجود", "موجوده", "موجودة", 
    "متوفر", "متوفرة", "متوفره", "متاح", "متاحة", "انا في", "أنا في", 
    "انا عند", "أنا عند", "واقف", "واقفه", "واقفة", "في الموقع", "بالخدمة"
]

LOCATIONS = [
    "الفضيلة", "الفضيله", "الرغامة", "الرغامه", "الخمرة", "الخمره", 
    "الوزيرية", "الوزيريه", "السنابل", "التيسير", "النسيم", "الأندلس", 
    "الاندلس", "الأندلس مول", "الاندلس مول", "الصناعية", "الزهراء", 
    "النخيل", "الصالحية", "الروضة", "الصفا", "المروة", "الجامعة", 
    "الحمراء", "الربوة", "النزهة", "المشرفة", "بني مالك", "الحمدانية", 
    "المحمدية", "الخالدية", "النعيم", "السلامة", "الشاطئ", "أبحر", 
    "ابحر", "التوفيق", "العدل", "المنار", "الواحة", "الفيصلية", 
    "الريان", "الوادي", "الفلاح", "النهضة", "الرابية", "السلام", "مكة", "جدة"
]

GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام", 
    "صباح الخير", "مساء الخير", "هلا", "اهلا", "مرحبا"
]


# ============================================================
# 💾 قاعدة البيانات
# ============================================================

class Database:

    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                role TEXT DEFAULT '',
                registration_date TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                customer_id INTEGER,
                customer_name TEXT,
                pickup TEXT,
                destination TEXT,
                trip_type TEXT DEFAULT 'normal',
                original_text TEXT DEFAULT '',
                created_at TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ready_drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                driver_id INTEGER,
                driver_name TEXT,
                created_at TEXT,
                UNIQUE(trip_id, driver_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                user_id INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_reason TEXT,
                updated_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS presence (
                user_id INTEGER PRIMARY KEY,
                location TEXT,
                last_date TEXT,
                updated_at TEXT
            )
        """)

        self.conn.commit()

    def save_user(self, user):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, name, username, registration_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET name = excluded.name, username = excluded.username
        """, (user.id, user.full_name, user.username or "", datetime.now(SAUDI_TZ).isoformat()))
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

    def create_trip(self, message_id, customer_id, customer_name, pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, customer_name, pickup, destination, trip_type, original_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, customer_id, customer_name, pickup, destination, trip_type, original_text, datetime.now(SAUDI_TZ).isoformat()))
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

    def add_ready_driver(self, trip_id, driver_id, driver_name):
        cur = self.conn.cursor()
        try:
            cur.execute("""
                INSERT INTO ready_drivers (trip_id, driver_id, driver_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (trip_id, driver_id, driver_name, datetime.now(SAUDI_TZ).isoformat()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_ready_drivers(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM ready_drivers WHERE trip_id = ? ORDER BY id ASC", (trip_id,))
        return [dict(row) for row in cur.fetchall()]

    def get_violation_count(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM violations WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row["count"] if row else 0

    def add_violation(self, user_id, reason):
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM violations WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            count = row["count"] + 1
            cur.execute("UPDATE violations SET count = ?, last_reason = ?, updated_at = ? WHERE user_id = ?", 
                        (count, reason, datetime.now(SAUDI_TZ).isoformat(), user_id))
        else:
            count = 1
            cur.execute("INSERT INTO violations (user_id, count, last_reason, updated_at) VALUES (?, ?, ?, ?)", 
                        (user_id, count, reason, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()
        return count

    def get_presence_today(self, user_id):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM presence WHERE user_id = ? AND last_date = ?", (user_id, today))
        row = cur.fetchone()
        return dict(row) if row else None

    def save_presence(self, user_id, location):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO presence (user_id, location, last_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET location = excluded.location, last_date = excluded.last_date, updated_at = excluded.updated_at
        """, (user_id, location, today, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()


# ============================================================
# 🤖 البوت والمنطق
# ============================================================

class SmartRidesBot:

    def __init__(self):
        self.db = Database()

    def normalize_text(self, text):
        if not text:
            return ""
        text = text.lower()
        replacements = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def contains_phone_number(self, text):
        if not text:
            return False
        translation = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        text = text.translate(translation)
        compact = re.sub(r"[\s\-\(\)]", "", text)
        patterns = [
            r"(?<!\d)05\d{8}(?!\d)",
            r"(?<!\d)5\d{8}(?!\d)",
            r"(?<!\d)9665\d{8}(?!\d)",
            r"(?<!\d)\+9665\d{8}(?!\d)",
        ]
        return any(re.search(p, compact) for p in patterns)

    def contains_private_word(self, text):
        normalized = self.normalize_text(text)
        words = re.findall(r"[\w\u0600-\u06FF]+", normalized)
        forbidden = {"خاص", "بالخاص", "للخاص", "خاصني", "خاصك"}
        return any(w in forbidden for w in words)

    def contains_unauthorized_link(self, text):
        if not text:
            return False
        links = re.findall(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)", text.lower())
        for link in links:
            if ALLOWED_GROUP_LINK.lower() in link:
                continue
            return True
        return False

    def extract_route(self, text):
        normalized = self.normalize_text(text)
        match = re.search(r"من\s+(.+?)\s+(?:الى|الي)\s+(.+)", normalized)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        found = []
        for location in LOCATIONS:
            if self.normalize_text(location) in normalized:
                if location not in found:
                    found.append(location)
        if len(found) >= 2:
            return found[0], found[1]
        return None, None

    def detect_trip(self, text):
        normalized = self.normalize_text(text)
        pickup, destination = self.extract_route(text)
        if not pickup or not destination:
            return None, None, None
        monthly = any(self.normalize_text(w) in normalized for w in MONTHLY_TRIP_WORDS)
        return ("monthly" if monthly else "normal"), pickup, destination

    def detect_presence(self, text):
        normalized = self.normalize_text(text)
        has_presence = any(self.normalize_text(w) in normalized for w in PRESENCE_WORDS)
        if not has_presence:
            return None
        for location in LOCATIONS:
            if self.normalize_text(location) in normalized:
                return location
        match = re.search(r"(?:في|ب|عند)\s+([^\s،,.]+)", normalized)
        return match.group(1) if match else None

    async def delete_message(self, message):
        try:
            await message.delete()
        except Exception:
            pass

    async def delete_later(self, context):
        try:
            await context.job.data.delete()
        except Exception:
            pass

    async def issue_violation(self, update, context, reason):
        message = update.effective_message
        user = update.effective_user
        if not message or not user:
            return

        count = self.db.add_violation(user.id, reason)
        await self.delete_message(message)

        if count == 1:
            text = f"⚠️ <b>تنبيه</b>\n\nيا {self.html(user.first_name)}، تم تسجيل المخالفة الأولى.\nالسبب: {reason}"
        elif count == 2:
            text = f"⚠️ <b>تحذير أخير</b>\n\nيا {self.html(user.first_name)}، تم تسجيل المخالفة الثانية.\n⚠️ الثالثة = كتم 24 ساعة."
        else:
            text = f"🚫 <b>تم كتمك لمدة 24 ساعة</b>\nالسبب: {reason}"

        try:
            warning = await context.bot.send_message(chat_id=message.chat_id, text=text, parse_mode=ParseMode.HTML)
            context.job_queue.run_once(self.delete_later, 8, data=warning)
        except Exception:
            pass

        if count >= 3:
            try:
                until_date = datetime.now(SAUDI_TZ) + timedelta(hours=24)
                await context.bot.restrict_chat_member(
                    chat_id=message.chat_id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
            except Exception:
                pass

    async def handle_new_member(self, update, context):
        message = update.effective_message
        if not message:
            return
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            self.db.save_user(member)
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👤 أنا عميل", callback_data=f"btn_customer:{member.id}"),
                    InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"btn_driver:{member.id}")
                ],
                [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")]
            ])
            welcome = await message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            context.job_queue.run_once(self.delete_later, 60, data=welcome)

    async def handle_presence(self, update, context, location):
        message = update.effective_message
        user = update.effective_user
        self.db.save_user(user)
        self.db.set_role(user.id, "driver")

        if self.db.get_presence_today(user.id):
            await self.issue_violation(update, context, "تكرار إعلان التواجد أكثر من مرة في اليوم")
            return

        self.db.save_presence(user.id, location)
        card = await message.reply_text(
            f"📍 <b>تم تسجيل تواجدك</b>\n\n🚕 الكابتن: {self.html(user.first_name)}\n📍 الموقع: {self.html(location)}",
            parse_mode=ParseMode.HTML
        )
        context.job_queue.run_once(self.delete_later, 20, data=card)

    async def handle_trip(self, update, context, trip_type, pickup, destination):
        message = update.effective_message
        user = update.effective_user
        self.db.save_user(user)
        self.db.set_role(user.id, "customer")

        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            customer_name=user.first_name or "العميل",
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            original_text=message.text or ""
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 جاهز", callback_data=f"take_trip:{trip_id}")],
            [InlineKeyboardButton("📩 التواصل مع الكابتن", callback_data=f"customer_contact:{trip_id}")],
            [InlineKeyboardButton("✅ تم المشوار", callback_data=f"close_trip:{trip_id}")]
        ])

        await message.reply_text(
            f"✅ <b>تم تسجيل طلبك</b>\n\n📍 من: {self.html(pickup)}\n🏁 إلى: {self.html(destination)}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    async def handle_take_trip(self, update, context):
        query = update.callback_query
        user = query.from_user
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return

        trip = self.db.get_trip(trip_id)
        if not trip or trip["status"] != "active":
            await query.answer("❌ المشوار غير متاح.", show_alert=True)
            return

        if user.id == trip["customer_id"]:
            await query.answer("😂 لا يمكنك أخذ مشوارك بنفسك.", show_alert=True)
            return

        self.db.save_user(user)
        self.db.set_role(user.id, "driver")

        if not self.db.add_ready_driver(trip_id, user.id, user.first_name or "الكابتن"):
            await query.answer("⚠️ أنت مسجل بالفعل لهذا المشوار.", show_alert=True)
            return

        await query.answer("✅ تم تسجيل جاهزيتك.", show_alert=True)

        # رسائل لفتح الخاص مباشرة
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🚕 <b>تم تسجيل كابتن للمشوار</b>\n\n👤 الكابتن: {self.html(user.first_name)}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📩 التواصل مع العميل", url=f"tg://user?id={trip['customer_id']}")]] )
        )

    async def handle_customer_contact(self, update, context):
        query = update.callback_query
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return

        drivers = self.db.get_ready_drivers(trip_id)
        if not drivers:
            await query.answer("⏳ لم يسجل أي كابتن جاهز حتى الآن.", show_alert=True)
            return

        buttons = [[InlineKeyboardButton(f"📩 التواصل مع {d['driver_name']}", url=f"tg://user?id={d['driver_id']}")] for d in drivers]
        await query.answer()
        await query.message.reply_text("اختر الكابتن للتواصل:", reply_markup=InlineKeyboardMarkup(buttons))

    async def handle_close_trip(self, update, context):
        query = update.callback_query
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return

        trip = self.db.get_trip(trip_id)
        if not trip or query.from_user.id != trip["customer_id"]:
            await query.answer("⚠️ صاحب الطلب فقط يستطيع الإغلاق.", show_alert=True)
            return

        self.db.close_trip(trip_id)
        await query.answer("✅ تم إغلاق المشوار.", show_alert=True)

    async def handle_callback_buttons(self, update, context):
        query = update.callback_query
        data = query.data or ""
        user = query.from_user

        if data.startswith("btn_customer:") or data.startswith("btn_driver:"):
            role = "customer" if "customer" in data else "driver"
            target_id = int(data.split(":")[1])
            if target_id != user.id:
                await query.answer("❌ هذا الزر غير مخصص لك.", show_alert=True)
                return
            self.db.save_user(user)
            self.db.set_role(user.id, role)
            await query.answer("✅ تم تحديث حالتك بنجاح.", show_alert=True)
            return

        if data == "btn_complaints":
            await query.answer()
            await query.message.reply_text(f"⚠️ للتواصل مع الإدارة:\n@{ADMIN_USERNAME}", parse_mode=ParseMode.HTML)

    async def handle_message(self, update, context):
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        if not message or not user or not chat:
            return

        # تحقق من القروب الصحيح
        if chat.id != GROUP_ID:
            return

        text = message.text or message.caption or ""
        if not text.strip():
            return

        self.db.save_user(user)

        if self.db.is_banned(user.id):
            return

        if self.contains_phone_number(text):
            await self.issue_violation(update, context, "نشر رقم جوال داخل القروب ممنوع")
            return

        if self.contains_private_word(text):
            await self.issue_violation(update, context, "كتابة كلمة «خاص» داخل القروب ممنوعة")
            return

        if self.contains_unauthorized_link(text):
            await self.issue_violation(update, context, "نشر الروابط أو الإعلانات الخارجية ممنوع")
            return

        location = self.detect_presence(text)
        if location:
            await self.handle_presence(update, context, location)
            return

        trip_type, pickup, destination = self.detect_trip(text)
        if trip_type:
            await self.handle_trip(update, context, trip_type, pickup, destination)
            return

        normalized = self.normalize_text(text).strip()
        for g in GREETINGS:
            if normalized == self.normalize_text(g):
                await message.reply_text("وعليكم السلام ورحمة الله وبركاته 🌹\nحياك الله في مشاوير جدة 🚘")
                return


# ============================================================
# أمر /start العام
# ============================================================

async def start_command(update, context):
    user = update.effective_user
    if user:
        # ربط صحيح بقاعدة البيانات عبر كلاس البوت أو إنشاء كائن مؤقت إذا لزم
        db_instance = Database()
        db_instance.save_user(user)

    await update.message.reply_text(
        "🚘 <b>مشاوير جدة وضواحيها</b>\n\nأهلاً بك 👋\n👤 العميل: اكتب طلبك مباشرة.\n🚕 الكابتن: اضغط جاهز.",
        parse_mode=ParseMode.HTML
    )


# ============================================================
# 🚀 نقطة التشغيل الرئيسية
# ============================================================

def main():
    if not TOKEN:
        raise RuntimeError("❌ لم يتم العثور على BOT_TOKEN في متغيرات البيئة.")

    bot_instance = SmartRidesBot()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_instance.handle_new_member))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_take_trip, pattern=r"^take_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_customer_contact, pattern=r"^customer_contact:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_close_trip, pattern=r"^close_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_callback_buttons, pattern=r"^btn_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message))

    logger.info("✅ تم تشغيل بوت مشاوير جدة بنجاح.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
