"""
🤖 بوت مشاوير جدة الذكي - النسخة المطورة
مع مميزات:
- تسجيل العملاء والكباتن
- حفظ الدور بعد التسجيل
- تسجيل تواجد الكابتن
- فهم اللهجات
- إنشاء بطاقات المشاوير
- زر أنا جاهز
- التواصل بين العميل والكابتن
- دعم الأسعار وروابط Google Maps
- قاعدة بيانات مستمرة بدون حذف عند إعادة التشغيل
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
    "شهري",
    "بالشهر",
    "كل يوم",
    "يوميا",
    "يومياً",
    "دوام",
    "مدرسة",
    "جامعة",
    "مشوار يومي",
    "توصيل يومي",
    "التزام",
    "مكان المنزل",
    "مكان الدوام",
    "عدد الايام",
    "عدد ايام الدوام",
    "اسبوعي",
    "أسبوعي",
    "شهر",
    "شهرين",
    "راتب",
    "مداوم",
    "كل اسبوع",
    "كل أسبوع",
    "monthly",
    "month",
    "daily",
    "every day",
    "everyday",
]


NORMAL_TRIP_WORDS = [
    "مشوار",
    "توصيل",
    "توصيلة",
    "يوصلني",
    "يوديني",
    "ابغى مشوار",
    "ابي مشوار",
    "احتاج توصيل",
    "ابغا مشوار",
    "من يوصلني",
    "فيه كابتن",
    "اوصلني",
    "ودني",
    "خذني",
    "نبغى",
    "نبي",
    "ابي",
    "أبي",
    "ابغا",
    "أبغا",
    "اريد",
    "أريد",
    "عايز",
    "محتاج",
    "محتاجة",
    "trip",
    "ride",
    "from",
    "to",
    "need",
    "pickup",
]


PRESENCE_WORDS = [
    "متواجد",
    "موجود",
    "انا في",
    "أنا في",
    "انا عند",
    "أنا عند",
    "متوفر",
    "مستعد",
    "جاهز",
    "في الانتظار",
    "بالخدمة",
    "متواجده",
    "موجوده",
    "متواجدة",
    "موجودة",
    "available",
    "here",
    "ready",
    "present",
    "online",
    "واقف",
    "واقفه",
    "واقفة",
    "انتظر",
    "مستني",
    "في الموقع",
    "بالموقع",
    "متجهز",
    "متجهزة",
]


LOCATIONS = [
    "الفضيلة",
    "الرغامة",
    "جدة",
    "مكة",
    "الرياض",
    "الدمام",
    "المدينة",
    "الطائف",
    "أبها",
    "تبوك",
    "جازان",
    "الجنوب",
    "الشمال",
    "الشرق",
    "الغرب",
    "البلد",
    "البغدادية",
    "الروضة",
    "الصفا",
    "المروة",
    "النسيم",
    "السليمانية",
    "العزيزية",
    "الفيحاء",
    "الجامعة",
    "الحمراء",
    "الاندلس",
    "الأندلس",
    "الربوة",
    "النزهة",
    "المشرفة",
    "بني مالك",
    "الهدا",
    "الشفا",
    "الحمدانية",
    "السنابل",
    "المداين",
    "السالم",
]


GREETINGS = [
    (
        ["السلام عليكم", "سلام عليكم"],
        ["وعليكم السلام 🌹🚘", "وعليكم السلام يا هلا 👋"],
    ),
    (
        ["هلا", "مرحبا", "اهلا"],
        ["هلا وغلا 🌹", "يا هلا والله 👋"],
    ),
    (
        ["صباح الخير"],
        ["صباح النور ☀️🌹"],
    ),
    (
        ["مساء الخير"],
        ["مساء النور 🌙🌹"],
    ),
]


CHAT_RESPONSES = [
    (
        ["كيفك", "كيف حالك"],
        ["بخير 🌹", "تمام 😊"],
    ),
    (
        ["وش تسوي"],
        ["أنتظر مشوارك 😎🚘"],
    ),
    (
        ["تحبني"],
        ["أحبك ❤️"],
    ),
    (
        ["نكت", "قول نكتة"],
        ["مرة كابتن نسى العميل وراح 😂"],
    ),
    (
        ["شسمك"],
        ["اسمي بوت المشاوير 😎"],
    ),
    (
        ["طفشان", "ملل"],
        ["اطلب مشوار وتروق 🚘"],
    ),
    (
        ["احبك", "حبيبي"],
        ["حبيبي أنت 🌹"],
    ),
    (
        ["كم السعر"],
        ["💰 السعر بالتفاهم 🤝"],
    ),
    (
        ["بوت", "يا بوت"],
        ["نعم أنا هنا 🤖"],
    ),
]


BAD_WORDS = [
    "يا غبي",
    "يا حمار",
    "انقلع",
]


# ============================================================
# 💾 قاعدة البيانات
# ============================================================

class Database:

    def __init__(self):
        self.db_file = DB_FILE
        self.init_db()

    def connect(self):
        con = sqlite3.connect(
            self.db_file,
            timeout=30,
            check_same_thread=False,
        )
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

    # --------------------------------------------------------

    def save_user(self, user):

        if not user:
            return

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                INSERT INTO users
                (user_id, name, username)
                VALUES (?, ?, ?)

                ON CONFLICT(user_id)
                DO UPDATE SET
                    name = excluded.name,
                    username = excluded.username
            """, (
                user.id,
                user.full_name,
                user.username or "",
            ))

            con.commit()

    # --------------------------------------------------------

    def set_role(self, user_id, role):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute(
                "UPDATE users SET role = ? WHERE user_id = ?",
                (role, user_id),
            )

            con.commit()

    # --------------------------------------------------------

    def get_role(self, user_id):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute(
                "SELECT role FROM users WHERE user_id = ?",
                (user_id,),
            )

            row = cur.fetchone()

            return row["role"] if row else ""

    # --------------------------------------------------------

    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"

    # --------------------------------------------------------

    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"

    # --------------------------------------------------------

    def create_trip(
        self,
        message_id,
        customer_id,
        pickup,
        destination,
        trip_type="normal",
        original_text="",
    ):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                INSERT OR REPLACE INTO trips
                (
                    message_id,
                    customer_id,
                    pickup,
                    destination,
                    trip_type,
                    original_text
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                customer_id,
                pickup,
                destination,
                trip_type,
                original_text,
            ))

            con.commit()

            return cur.lastrowid

    # --------------------------------------------------------

    def get_trip(self, trip_id):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute(
                "SELECT * FROM trips WHERE trip_id = ?",
                (trip_id,),
            )

            row = cur.fetchone()

            return dict(row) if row else None

    # --------------------------------------------------------

    def add_ready_driver(self, trip_id, driver_id):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                INSERT OR IGNORE INTO ready_drivers
                (trip_id, driver_id)
                VALUES (?, ?)
            """, (
                trip_id,
                driver_id,
            ))

            con.commit()

            return cur.rowcount > 0

    # --------------------------------------------------------

    def is_driver_ready(self, trip_id, driver_id):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                SELECT 1
                FROM ready_drivers
                WHERE trip_id = ?
                AND driver_id = ?
            """, (
                trip_id,
                driver_id,
            ))

            return cur.fetchone() is not None

    # --------------------------------------------------------

    def set_presence(self, driver_id, location):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                INSERT INTO driver_presence
                (driver_id, location)
                VALUES (?, ?)

                ON CONFLICT(driver_id)
                DO UPDATE SET
                    location = excluded.location,
                    last_update = CURRENT_TIMESTAMP
            """, (
                driver_id,
                location,
            ))

            con.commit()

    # --------------------------------------------------------

    def get_presence(self, driver_id):

        with self.connect() as con:

            cur = con.cursor()

            cur.execute("""
                SELECT *
                FROM driver_presence
                WHERE driver_id = ?
            """, (driver_id,))

            row = cur.fetchone()

            return dict(row) if row else None


# ============================================================
# 🤖 البوت
# ============================================================

class SmartRidesBot:

    def __init__(self):
        self.db = Database()

    # ========================================================
    # تنظيف النص
    # ========================================================

    def normalize_text(self, text):

        replacements = {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ى": "ي",
            "ة": "ه",
            "ؤ": "و",
            "ئ": "ي",
            "ء": "",
            "ٱ": "ا",
            "ڪ": "ك",
            "ﮐ": "ك",
            "ڿ": "ك",
        }

        text = text.lower()

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    # ========================================================

    def html(self, text):

        if not text:
            return ""

        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    # ========================================================
    # كشف نوع المشوار
    # ========================================================

    def detect_trip_type(self, text):

        normalized = self.normalize_text(text)

        for word in MONTHLY_TRIP_WORDS:

            if self.normalize_text(word) in normalized:
                return "monthly"

        for word in NORMAL_TRIP_WORDS:

            if self.normalize_text(word) in normalized:
                return "normal"

        if re.search(
            r"من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            normalized,
            re.IGNORECASE,
        ):
            return "normal"

        return None

    # ========================================================
    # كشف التواجد
    # ========================================================

    def detect_presence(self, text):

        normalized = self.normalize_text(text)

        for word in PRESENCE_WORDS:

            word_normalized = self.normalize_text(word)

            if word_normalized in normalized:
                return True

        return False

    # ========================================================
    # استخراج الموقع
    # ========================================================

    def extract_location(self, text):

        normalized = self.normalize_text(text)

        for loc in LOCATIONS:

            if self.normalize_text(loc) in normalized:
                return loc

        patterns = [
            r"(?:انا|أنا)\s+(?:متواجد|موجود|متوفر|جاهز)\s+(?:في|ب|بـ)\s+(.+)",
            r"(?:متواجد|موجود|متوفر)\s+(?:في|ب|بـ)\s+(.+)",
            r"(?:انا|أنا)\s+(?:في|عند)\s+(.+)",
            r"(?:في|عند)\s+(.+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                location = match.group(1).strip()

                location = re.sub(
                    r"[.!،,]+$",
                    "",
                    location,
                )

                if location:
                    return location

        return None

    # ========================================================
    # هل النص مشوار؟
    # ========================================================

    def looks_like_trip(self, text):

        normalized = self.normalize_text(text)

        # الكابتن إذا كان يعلن وجوده لا نحوله لمشوار
        if self.detect_presence(text):

            # إذا كانت الرسالة واضحة كتواجد فقط
            route_exists = bool(
                re.search(
                    r"من\s+.+?\s+(?:الى|الي|لل)\s+.+",
                    normalized,
                    re.IGNORECASE,
                )
            )

            if not route_exists and not any(
                self.normalize_text(word) in normalized
                for word in [
                    "ابغى",
                    "ابي",
                    "احتاج",
                    "يوصلني",
                    "يوديني",
                    "مشوار",
                    "توصيل",
                    "توصيله",
                ]
            ):
                return False

        if self.detect_trip_type(text):
            return True

        if re.search(
            r"من\s+.+?\s+(?:الى|الي|لل)\s+.+",
            normalized,
            re.IGNORECASE,
        ):
            return True

        trip_indicators = [
            "مكان المنزل",
            "مكان الدوام",
            "لوكيشن",
            "السعر",
            "التزام",
            "مشوار",
            "توصيل",
            "عدد الايام",
            "عدد ايام الدوام",
            "دوام",
            "يوصلني",
            "يوديني",
            "اوصلني",
            "ودني",
            "خذني",
        ]

        for word in trip_indicators:

            if self.normalize_text(word) in normalized:
                return True

        return False

    # ========================================================
    # استخراج الطريق
    # ========================================================

    def extract_route(self, text):

        normalized = self.normalize_text(text)

        match = re.search(
            r"من\s+(.+?)\s+(?:الى|الي|لل)\s+(.+)",
            normalized,
            re.IGNORECASE,
        )

        if match:

            return (
                match.group(1).strip(),
                match.group(2).strip(),
            )

        home_match = re.search(
            r"مكان\s+المنزل\s*[:：\-]?\s*(.+)",
            text,
            re.IGNORECASE,
        )

        work_match = re.search(
            r"مكان\s+الدوام\s*[:：\-]?\s*(.+)",
            text,
            re.IGNORECASE,
        )

        if home_match and work_match:

            return (
                home_match.group(1).strip(),
                work_match.group(1).strip(),
            )

        return None, None

    # ========================================================
    # استخراج السعر
    # ========================================================

    def extract_price(self, text):

        patterns = [
            r"(?:السعر|سعر|المبلغ|بـ|ب)\s*[:：]?\s*(\d+)\s*(?:ريال|ر\.س|ر)?",
            r"(\d+)\s*(?:ريال|ر\.س)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return None

    # ========================================================
    # Google Maps
    # ========================================================

    def extract_maps_links(self, text):

        links = re.findall(
            r"https?://(?:www\.)?(?:google\.[^/\s]+|maps\.google\.[^/\s]+)[^\s<>]+",
            text,
            re.IGNORECASE,
        )

        return links

    # ========================================================
    # الردود
    # ========================================================

    def get_chat_response(self, text):

        normalized = self.normalize_text(text)

        for phrases, responses in CHAT_RESPONSES:

            for phrase in phrases:

                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)

        return None

    # ========================================================

    def get_greeting(self, text):

        normalized = self.normalize_text(text)

        for phrases, responses in GREETINGS:

            for phrase in phrases:

                if normalized.startswith(
                    self.normalize_text(phrase)
                ):
                    return random.choice(responses)

        return None

    # ========================================================
    # الترحيب
    # ========================================================

    async def welcome_new_member(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        message = update.message

        if not message:
            return

        for member in message.new_chat_members:

            if member.is_bot:
                continue

            self.db.save_user(member)

            welcome_text = f"""
🌟 <b>يا هلا {self.html(member.full_name)}!</b>

نورت <b>{GROUP_NAME}</b> 🚘

👤 <b>عميل:</b> اكتب طلبك مباشرة.
🚕 <b>كابتن:</b> سجل نفسك ثم أعلن موقعك.

✍️ <b>للتسجيل:</b>
اكتب «أنا كابتن» أو «أنا عميل»
"""

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "👤 أنا عميل",
                        callback_data=f"role_customer:{member.id}",
                    ),
                    InlineKeyboardButton(
                        "🚕 أنا كابتن",
                        callback_data=f"role_driver:{member.id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📋 قانون القروب",
                        callback_data="rules",
                    ),
                    InlineKeyboardButton(
                        "📩 الإدارة",
                        url=f"https://t.me/{ADMIN_USERNAME}",
                    ),
                ],
            ])

            await message.reply_text(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )

    # ========================================================
    # اختيار الدور
    # ========================================================

    async def role_selection(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        data = query.data
        user = query.from_user

        try:
            await query.answer()
        except Exception:
            pass

        if not data:
            return

        try:
            target_id = int(data.split(":")[1])
        except (IndexError, ValueError):
            return

        # فقط العضو المقصود أو الإدارة
        is_admin = user.id in ADMIN_IDS

        if not is_admin:

            try:

                member = await context.bot.get_chat_member(
                    GROUP_ID,
                    user.id,
                )

                is_admin = member.status in (
                    "administrator",
                    "creator",
                )

            except Exception:
                is_admin = False

        if user.id != target_id and not is_admin:

            await query.answer(
                "⚠️ هذا الزر مخصص للعضو الجديد فقط!",
                show_alert=True,
            )

            return

        if data.startswith("role_customer:"):

            role = "customer"

            role_text = (
                "✅ <b>تم تسجيلك كعميل!</b>\n\n"
                "الآن اكتب مشوارك مباشرة 🚗"
            )

        elif data.startswith("role_driver:"):

            role = "driver"

            role_text = (
                "✅ <b>تم تسجيلك ككابتن!</b>\n\n"
                "الآن أعلن موقعك مثل:\n"
                "📍 أنا متواجد في الحمدانية"
            )

        else:
            return

        self.db.save_user(user)
        self.db.set_role(target_id, role)

        await query.message.reply_text(
            role_text,
            parse_mode=ParseMode.HTML,
        )

    # ========================================================
    # القوانين
    # ========================================================

    async def show_rules(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query

        await query.answer()

        await query.message.reply_text(
            RULES_TEXT,
            parse_mode=ParseMode.HTML,
        )

    # ========================================================
    # معالجة الرسائل
    # ========================================================

    async def handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        message = update.message
        user = update.effective_user

        if not message or not user:
            return

        self.db.save_user(user)

        text = message.text or message.caption or ""

        if not text:
            return

        normalized_text = self.normalize_text(text).strip()

        # ====================================================
        # تسجيل كابتن
        # ====================================================

        if normalized_text in [
            "انا كابتن",
            "انا سايق",
            "انا سواق",
            "كابتن",
        ]:

            self.db.set_role(
                user.id,
                "driver",
            )

            await message.reply_text(
                "✅ <b>تم تسجيلك ككابتن!</b>\n\n"
                "لن أطلب منك التسجيل مرة أخرى بإذن الله. 👍\n\n"
                "📍 أعلن موقعك مثل:\n"
                "أنا متواجد في الحمدانية",
                parse_mode=ParseMode.HTML,
            )

            return

        # ====================================================
        # تسجيل عميل
        # ====================================================

        if normalized_text in [
            "انا عميل",
            "انا زبون",
            "انا طالب",
            "عميل",
        ]:

            self.db.set_role(
                user.id,
                "customer",
            )

            await message.reply_text(
                "✅ <b>تم تسجيلك كعميل!</b>\n\n"
                "الآن اكتب مشوارك مباشرة 🚗\n\n"
                "مثال:\n"
                "من الفضيلة إلى الرغامة",
                parse_mode=ParseMode.HTML,
            )

            return

        # ====================================================
        # التواجد
        # ====================================================

        if self.detect_presence(text):

            user_role = self.db.get_role(user.id)

            # الكابتن المسجل
            if user_role == "driver":

                location = (
                    self.extract_location(text)
                    or "غير محدد"
                )

                self.db.set_presence(
                    user.id,
                    location,
                )

                now = datetime.now(SAUDI_TZ)

                presence_card = f"""
📍 <b>تم تسجيل تواجدك بنجاح!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(user.full_name)}
🚕 <b>الموقع:</b> {self.html(location)}
🕐 <b>الوقت:</b> {now.strftime('%H:%M')}

🙏 <b>الله يرزقك المشوار الطيب!</b>
"""

                await message.reply_text(
                    presence_card,
                    parse_mode=ParseMode.HTML,
                )

                return

            # العميل
            elif user_role == "customer":

                # إذا كانت الرسالة مشوار فعلي لا نوقفها
                if not self.looks_like_trip(text):

                    await message.reply_text(
                        "⚠️ <b>خاصية التواجد للكباتن فقط.</b>\n\n"
                        "إذا عندك مشوار، اكتبه مباشرة 🚗",
                        parse_mode=ParseMode.HTML,
                    )

                    return

            # غير مسجل
            else:

                # إذا كانت الرسالة مجرد تواجد
                if not self.looks_like_trip(text):

                    await message.reply_text(
                        "📝 <b>سجل نوعك أولاً!</b>\n\n"
                        "🚕 للكابتن: اكتب «أنا كابتن»\n"
                        "👤 للعميل: اكتب «أنا عميل»",
                        parse_mode=ParseMode.HTML,
                    )

                    return

        # ====================================================
        # طلب مشوار
        # ====================================================

        if self.looks_like_trip(text):

            # الكابتن لا يتم التعامل مع كلامه كمشوار
            # إلا إذا كان واضحًا أنه يطلب مشوارًا لنفسه
            if self.db.is_driver(user.id):

                explicit_customer_words = [
                    "ابغى",
                    "ابي",
                    "أبي",
                    "احتاج",
                    "محتاج",
                    "محتاجه",
                    "يوصلني",
                    "يوديني",
                    "خذني",
                    "ودني",
                    "من يوصلني",
                    "ابي توصيل",
                    "ابغا توصيل",
                ]

                normalized = self.normalize_text(text)

                is_explicit_request = any(
                    self.normalize_text(word) in normalized
                    for word in explicit_customer_words
                )

                has_route = bool(
                    re.search(
                        r"من\s+.+?\s+(?:الى|الي|لل)\s+.+",
                        normalized,
                        re.IGNORECASE,
                    )
                )

                if not is_explicit_request and not has_route:
                    return

            await self.handle_trip_request(
                update,
                context,
                text,
            )

            return

        # ====================================================
        # ردود ذكية
        # ====================================================

        chat_response = self.get_chat_response(text)

        if chat_response:

            await message.reply_text(
                chat_response,
            )

            return

        # ====================================================
        # تحية
        # ====================================================

        greeting = self.get_greeting(text)

        if greeting:

            await message.reply_text(
                greeting,
            )

            return

    # ========================================================
    # إنشاء المشوار
    # ========================================================

    async def handle_trip_request(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text,
    ):

        message = update.message
        user = update.effective_user

        pickup, destination = self.extract_route(text)

        if not pickup or not destination:

            pickup = "غير محدد"
            destination = "غير محدد"

        trip_type = (
            self.detect_trip_type(text)
            or "normal"
        )

        price = self.extract_price(text)

        maps_links = self.extract_maps_links(text)

        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            original_text=text,
        )

        type_badge = (
            "🔄 شهري"
            if trip_type == "monthly"
            else "🚗 عادي"
        )

        details = self.html(text)

        extra = ""

        if price:
            extra += (
                f"\n💰 <b>السعر المذكور:</b> "
                f"{self.html(price)} ريال"
            )

        if maps_links:

            extra += (
                "\n📍 <b>Google Maps:</b> "
                "مرفق في تفاصيل الطلب"
            )

        confirm_text = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>نوع المشوار:</b> {type_badge}

📝 <b>تفاصيل الطلب:</b>
{details}
{extra}

🚕 <b>للكباتن:</b>
إذا كنت كابتنًا جاهزًا للمشوار اضغط الزر بالأسفل 👇
"""

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🚕 أنا جاهز للمشوار",
                    callback_data=f"take_trip:{trip_id}:{user.id}",
                ),
            ],
        ])

        await message.reply_text(
            confirm_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=False,
        )

    # ========================================================
    # الكابتن جاهز
    # ========================================================

    async def handle_take_trip(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query
        driver = query.from_user

        try:
            data = query.data.split(":")

            trip_id = int(data[1])
            customer_id = int(data[2])

        except (IndexError, ValueError):

            await query.answer(
                "⚠️ حدث خطأ في بيانات المشوار.",
                show_alert=True,
            )

            return

        # العميل لا يستطيع أخذ مشواره
        if driver.id == customer_id:

            await query.answer(
                "😂 ما تقدر تأخذ مشوارك بنفسك!",
                show_alert=True,
            )

            return

        self.db.save_user(driver)

        # ====================================================
        # مهم:
        # لا يتم تحويل الشخص إلى كابتن تلقائيًا
        # ====================================================

        if not self.db.is_driver(driver.id):

            await query.answer(
                "⚠️ لازم تسجل نفسك ككابتن أولاً.\n\n"
                "اكتب: أنا كابتن",
                show_alert=True,
            )

            return

        # تسجيل الجاهزية
        added = self.db.add_ready_driver(
            trip_id,
            driver.id,
        )

        if not added:

            await query.answer(
                "✅ أنت مسجل جاهز لهذا المشوار بالفعل!",
                show_alert=True,
            )

            return

        trip = self.db.get_trip(trip_id)

        if not trip:

            await query.answer(
                "⚠️ المشوار غير موجود!",
                show_alert=True,
            )

            return

        type_badge = (
            "🔄 شهري"
            if trip["trip_type"] == "monthly"
            else "🚗 عادي"
        )

        original_text = trip.get(
            "original_text",
            "",
        )

        price = self.extract_price(
            original_text
        )

        price_text = (
            f"{self.html(price)} ريال"
            if price
            else "بالتفاهم بالخاص"
        )

        card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}

📋 <b>نوع المشوار:</b> {type_badge}

📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}

💰 <b>السعر:</b> {price_text}
"""

        if original_text:

            card_text += (
                "\n📝 <b>تفاصيل الطلب:</b>\n"
                f"{self.html(original_text)}\n"
            )

        contact_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📩 تواصل مع العميل",
                    callback_data=(
                        f"contact_customer:"
                        f"{trip_id}:"
                        f"{driver.id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🚕 تواصل مع الكابتن",
                    callback_data=(
                        f"contact_driver:"
                        f"{trip_id}:"
                        f"{driver.id}"
                    ),
                ),
            ],
        ])

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=card_text,
            parse_mode=ParseMode.HTML,
            reply_markup=contact_keyboard,
            disable_web_page_preview=False,
        )

        await query.answer(
            "✅ تم تسجيلك للمشوار!",
            show_alert=True,
        )

    # ========================================================
    # التواصل مع العميل
    # ========================================================

    async def contact_customer(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query
        user = query.from_user

        try:

            data = query.data.split(":")

            trip_id = int(data[1])
            driver_id = int(data[2])

        except (IndexError, ValueError):

            await query.answer(
                "⚠️ بيانات غير صحيحة.",
                show_alert=True,
            )

            return

        # فقط الكابتن المحدد
        if user.id != driver_id:

            await query.answer(
                "⚠️ هذا الزر مخصص للكابتن المحدد فقط.",
                show_alert=True,
            )

            return

        # يجب أن يكون كابتنًا مسجلًا
        if not self.db.is_driver(user.id):

            await query.answer(
                "⚠️ أنت غير مسجل ككابتن.",
                show_alert=True,
            )

            return

        # يجب أن يكون ضغط أنا جاهز
        if not self.db.is_driver_ready(
            trip_id,
            user.id,
        ):

            await query.answer(
                "⚠️ لازم تضغط «أنا جاهز للمشوار» أولاً.",
                show_alert=True,
            )

            return

        trip = self.db.get_trip(trip_id)

        if not trip:

            await query.answer(
                "⚠️ المشوار غير موجود.",
                show_alert=True,
            )

            return

        await query.answer(
            "📩 فتح تواصل العميل...",
            url=f"tg://user?id={trip['customer_id']}",
        )

    # ========================================================
    # التواصل مع الكابتن
    # ========================================================

    async def contact_driver(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        query = update.callback_query
        user = query.from_user

        try:

            data = query.data.split(":")

            trip_id = int(data[1])
            driver_id = int(data[2])

        except (IndexError, ValueError):

            await query.answer(
                "⚠️ بيانات غير صحيحة.",
                show_alert=True,
            )

            return

        trip = self.db.get_trip(trip_id)

        if not trip:

            await query.answer(
                "⚠️ المشوار غير موجود.",
                show_alert=True,
            )

            return

        # العميل صاحب الطلب فقط
        if trip["customer_id"] != user.id:

            await query.answer(
                "⚠️ هذا الزر مخصص لصاحب الطلب فقط.",
                show_alert=True,
            )

            return

        # يجب أن يكون الكابتن جاهزًا
        if not self.db.is_driver_ready(
            trip_id,
            driver_id,
        ):

            await query.answer(
                "⚠️ هذا الكابتن غير مسجل كمستعد للمشوار.",
                show_alert=True,
            )

            return

        await query.answer(
            "🚕 فتح تواصل الكابتن...",
            url=f"tg://user?id={driver_id}",
        )

    # ========================================================
    # START
    # ========================================================

    async def cmd_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not update.message:
            return

        await update.message.reply_text(
            f"🚘 <b>{GROUP_NAME}</b>\n\n"
            "🤖 البوت يعمل ✅\n\n"
            "👤 <b>عميل:</b> اكتب مشوارك.\n"
            "🚕 <b>كابتن:</b> اكتب موقعك.\n\n"
            "/help للمساعدة\n"
            "/rules للقوانين",
            parse_mode=ParseMode.HTML,
        )

    # ========================================================
    # RULES
    # ========================================================

    async def cmd_rules(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not update.message:
            return

        await update.message.reply_text(
            RULES_TEXT,
            parse_mode=ParseMode.HTML,
        )

    # ========================================================
    # HELP
    # ========================================================

    async def cmd_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        if not update.message:
            return

        help_text = """
🤖 <b>مساعدة بوت مشاوير جدة</b>

👤 <b>للعملاء:</b>
اكتب مشوارك مباشرة.

مثال:
من الفضيلة إلى الرغامة

📅 <b>مشوار شهري:</b>
مثال:
مشوار شهري من جدة إلى مكة

💰 <b>السعر:</b>
يمكن كتابة السعر داخل الطلب.

📍 <b>Google Maps:</b>
يمكن إرسال رابط Google Maps مع الطلب.

🚕 <b>للكباتن:</b>
سجل نفسك مرة واحدة:

«أنا كابتن»

ثم أعلن موقعك:

«أنا متواجد في الحمدانية»

بعد التسجيل لن يطلب منك البوت كتابة «أنا كابتن» كل مرة.

🟢 <b>جاهز للمشوار:</b>
اضغط زر «أنا جاهز للمشوار» تحت طلب العميل.

💡 البوت يحاول فهم اللهجات والصياغات المختلفة.
"""

        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )

    # ========================================================
    # تذكير
    # ========================================================

    async def smart_reminder(
        self,
        context: ContextTypes.DEFAULT_TYPE,
    ):

        current_hour = datetime.now(
            SAUDI_TZ
        ).hour

        if 2 <= current_hour < 8:
            return

        reminders = [
            (
                "🌅 <b>صباح الخير!</b>\n\n"
                "من عنده مشوار؟ 🚕"
            ),
            (
                "🚕 <b>الكباتن!</b>\n\n"
                "أعلنوا مواقعكم 📍\n"
                "مثال: أنا متواجد في الحمدانية"
            ),
            (
                "📢 <b>تذكير:</b>\n\n"
                "العملاء اكتبوا مشاويركم 🚗\n"
                "والكباتن سجلوا تواجدكم 📍"
            ),
        ]

        text = random.choice(reminders)

        try:

            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode=ParseMode.HTML,
            )

        except Exception as e:

            logging.warning(
                "تعذر إرسال التذكير: %s",
                e,
            )

    # ========================================================
    # تشغيل البوت
    # ========================================================

    async def post_init(
        self,
        application: Application,
    ):

        await application.bot.set_my_commands([
            BotCommand(
                "start",
                "بدء البوت",
            ),
            BotCommand(
                "rules",
                "قوانين القروب",
            ),
            BotCommand(
                "help",
                "المساعدة",
            ),
        ])

    # ========================================================

    def run(self):

        if not TOKEN:

            raise RuntimeError(
                "❌ BOT_TOKEN غير موجود. "
                "ضع التوكن الجديد في متغير البيئة BOT_TOKEN."
            )

        app = (
            Application.builder()
            .token(TOKEN)
            .post_init(self.post_init)
            .build()
        )

        # ====================================================
        # التذكير الدوري
        # ====================================================

        if app.job_queue:

            app.job_queue.run_repeating(
                self.smart_reminder,
                interval=ENGAGEMENT_INTERVAL,
                first=60,
            )

        # ====================================================
        # الأوامر
        # ====================================================

        app.add_handler(
            CommandHandler(
                "start",
                self.cmd_start,
            )
        )

        app.add_handler(
            CommandHandler(
                "rules",
                self.cmd_rules,
            )
        )

        app.add_handler(
            CommandHandler(
                "help",
                self.cmd_help,
            )
        )

        # ====================================================
        # الأعضاء الجدد
        # ====================================================

        app.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.welcome_new_member,
            )
        )

        # ====================================================
        # الأزرار
        # ====================================================

        app.add_handler(
            CallbackQueryHandler(
                self.role_selection,
                pattern=r"^role_",
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                self.show_rules,
                pattern=r"^rules$",
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                self.handle_take_trip,
                pattern=r"^take_trip:",
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                self.contact_customer,
                pattern=r"^contact_customer:",
            )
        )

        app.add_handler(
            CallbackQueryHandler(
                self.contact_driver,
                pattern=r"^contact_driver:",
            )
        )

        # ====================================================
        # الرسائل النصية
        # ====================================================

        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message,
            )
        )

        print("======================================")
        print("🤖 Smart Rides Bot")
        print("🚘 مشاوير جدة")
        print("✅ البوت يعمل...")
        print("💾 قاعدة البيانات محفوظة")
        print("======================================")

        app.run_polling(
            allowed_updates=Update.ALL_TYPES
        )


# ============================================================
# 🚀 نقطة البداية
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        format=(
            "%(asctime)s - "
            "%(levelname)s - "
            "%(message)s"
        ),
        level=logging.INFO,
    )

    # ❗ مهم:
    # لا تحذف قاعدة البيانات عند التشغيل.
    # كانت النسخة القديمة تحتوي على os.remove(DB_FILE)
    # وهذا كان يمسح تسجيل الكباتن والعملاء بعد كل Restart.

    bot = SmartRidesBot()

    bot.run()
