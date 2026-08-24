import os
import re
import sqlite3
import logging
import random
import unicodedata

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
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# SETTINGS
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_ID = -1003716441020

GROUP_NAME = "🚘 مشاوير جدة وضواحيها"

ADMIN_USERNAME = "klodi500"
OWNER_USERNAME = "klodi500"

ALLOWED_GROUP_LINK = "https://t.me/JeddahRides"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

MUTE_HOURS = 24
VIOLATION_RESET_DAYS = 30
ADMIN_CACHE_SECONDS = 300

REMINDER_INTERVAL = 30 * 60

# عدد الرسائل التي يحتفظ بها البوت في سياق العضو
CONTEXT_LIMIT = 8

# ============================================================
# التذكير
# ============================================================

INTERACTIVE_REMINDERS = [
    (
        "🚘🔥 <b>يا كباتن وعملاء {GROUP_NAME}!</b>\n\n"
        "خلونا نزيد التفاعل ونوصل القروب لأكبر عدد 🙌\n"
        "📢 انشر رابط القروب للي يحتاج مشاوير أو يقدم خدمة توصيل.\n\n"
        "🔗 {ALLOWED_GROUP_LINK}"
    ),
    (
        "📣 <b>تذكير سريع يا أهل المشاوير ❤️</b>\n\n"
        "عندك صاحب أو زميل يحتاج مشاوير؟\n"
        "أرسل له رابط القروب وخله ينضم معنا 🚘🔥\n\n"
        "🔗 {ALLOWED_GROUP_LINK}"
    ),
    (
        "🚕 <b>كباتننا وينكم؟ 😎🔥</b>\n"
        "🧑🏻‍💼 <b>وعملائنا وينكم؟ ❤️</b>\n\n"
        "خلونا نكبر القروب ونزيد الطلبات والمشاوير.\n"
        "شارك الرابط مع اللي تعرفهم 👇\n\n"
        "🔗 {ALLOWED_GROUP_LINK}"
    ),
    (
        "🔥 <b>كل عضو جديد = فرصة مشوار جديدة 🚘</b>\n\n"
        "لا تبخلون على القروب بالنشر ❤️\n"
        "شاركوا الرابط مع الأهل والأصدقاء والزملاء.\n\n"
        "🔗 {ALLOWED_GROUP_LINK}"
    ),
    (
        "🚘❤️ <b>خلونا نخلي القروب مليان مشاوير!</b>\n\n"
        "الكابتن يحتاج عملاء 👨‍✈️\n"
        "والعميل يحتاج كابتن 🚕\n\n"
        "وأفضل طريقة نزيد الفرص هي نشر القروب 📢🔥\n\n"
        "🔗 {ALLOWED_GROUP_LINK}"
    ),
]

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# TOKEN
# ============================================================

if not TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في GitHub Secrets.")

# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    with db() as con:
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                is_driver INTEGER DEFAULT 0,
                is_customer INTEGER DEFAULT 0,
                violations INTEGER DEFAULT 0,
                last_violation_at TEXT,
                last_message TEXT DEFAULT '',
                last_intent TEXT DEFAULT '',
                last_seen TEXT DEFAULT ''
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                user_id INTEGER PRIMARY KEY,
                last_date TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                message_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                customer_username TEXT DEFAULT '',
                created_at TEXT,
                start TEXT,
                destination TEXT,
                original_text TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ready (
                trip_id INTEGER,
                driver_id INTEGER,
                UNIQUE(trip_id, driver_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                intent TEXT,
                created_at TEXT
            )
        """)

        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]

        if "is_driver" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN is_driver INTEGER DEFAULT 0
            """)

        if "is_customer" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN is_customer INTEGER DEFAULT 0
            """)

        if "violations" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN violations INTEGER DEFAULT 0
            """)

        if "last_violation_at" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN last_violation_at TEXT
            """)

        if "last_message" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN last_message TEXT DEFAULT ''
            """)

        if "last_intent" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN last_intent TEXT DEFAULT ''
            """)

        if "last_seen" not in columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN last_seen TEXT DEFAULT ''
            """)

        cur.execute("PRAGMA table_info(trips)")
        trip_columns = [row[1] for row in cur.fetchall()]

        if "customer_username" not in trip_columns:
            cur.execute("""
                ALTER TABLE trips
                ADD COLUMN customer_username TEXT DEFAULT ''
            """)

        con.commit()


# ============================================================
# USERS
# ============================================================

def save_user(user):
    if not user:
        return

    now = datetime.now(SAUDI_TZ).isoformat()

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            INSERT INTO users (
                user_id,
                name,
                username,
                last_seen
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                name = excluded.name,
                username = excluded.username,
                last_seen = excluded.last_seen
        """, (
            user.id,
            user.full_name,
            user.username or "",
            now,
        ))

        con.commit()


def mark_driver(user):
    save_user(user)

    with db() as con:
        con.execute("""
            UPDATE users
            SET is_driver = 1,
                is_customer = 0
            WHERE user_id = ?
        """, (user.id,))
        con.commit()


def mark_customer(user):
    save_user(user)

    with db() as con:
        con.execute("""
            UPDATE users
            SET is_customer = 1,
                is_driver = 0
            WHERE user_id = ?
        """, (user.id,))
        con.commit()


def mark_driver_by_id(user_id):
    with db() as con:
        con.execute("""
            UPDATE users
            SET is_driver = 1,
                is_customer = 0
            WHERE user_id = ?
        """, (user_id,))
        con.commit()


def mark_customer_by_id(user_id):
    with db() as con:
        con.execute("""
            UPDATE users
            SET is_customer = 1,
                is_driver = 0
            WHERE user_id = ?
        """, (user_id,))
        con.commit()


def get_user_info(user_id):
    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT user_id, name, username,
                   is_driver, is_customer,
                   violations, last_message,
                   last_intent, last_seen
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        return cur.fetchone()


def is_driver(user_id):
    with db() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT is_driver
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()

    return bool(row and row[0] == 1)


def is_customer(user_id):
    with db() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT is_customer
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()

    return bool(row and row[0] == 1)


def get_username(user_id):
    with db() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT username
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        row = cur.fetchone()

    return row[0] if row and row[0] else ""


# ============================================================
# SMART CONTEXT
# ============================================================

def save_context(user_id, message_text, intent):
    now = datetime.now(SAUDI_TZ).isoformat()

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            INSERT INTO user_context (
                user_id,
                message_text,
                intent,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            clean_text(message_text),
            intent,
            now,
        ))

        cur.execute("""
            DELETE FROM user_context
            WHERE user_id = ?
            AND id NOT IN (
                SELECT id
                FROM user_context
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
        """, (
            user_id,
            user_id,
            CONTEXT_LIMIT,
        ))

        cur.execute("""
            UPDATE users
            SET last_message = ?,
                last_intent = ?,
                last_seen = ?
            WHERE user_id = ?
        """, (
            clean_text(message_text),
            intent,
            now,
            user_id,
        ))

        con.commit()


def get_last_context(user_id):
    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT message_text, intent, created_at
            FROM user_context
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))

        return cur.fetchone()


def get_context_history(user_id, limit=5):
    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT message_text, intent, created_at
            FROM user_context
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit))

        return cur.fetchall()


# ============================================================
# HELPERS
# ============================================================

def html(text):
    if not text:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def clean_text(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def remove_diacritics(text):
    if not text:
        return ""

    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def normalize_arabic(text):
    text = clean_text(text).lower()

    text = remove_diacritics(text)

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        "ـ": "",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # إزالة التكرار المبالغ فيه للحروف
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)

    return text


def compact_arabic(text):
    text = normalize_arabic(text)
    return re.sub(r"[\s\-_.،,!?؟:؛]+", "", text)


def contains_phrase(text, phrase):
    normalized = normalize_arabic(text)
    target = normalize_arabic(phrase)

    return target in normalized


def display_user(user):
    if not user:
        return "عضو"

    name = html(user.full_name)

    return f"<b>{name}</b>"


def display_saved_user(user_id):
    row = get_user_info(user_id)

    if not row:
        return "العضو"

    name = row[1]

    return f"<b>{html(name or 'عضو')}</b>"


def is_owner(user):
    if not user:
        return False

    if user.id == 952638746:
        return True

    if user.username:
        return user.username.lower() == OWNER_USERNAME.lower()

    return False


_admin_cache = {}


async def is_admin(update, context):
    user = update.effective_user

    if not user:
        return False

    if is_owner(user):
        return True

    now = datetime.now(SAUDI_TZ)

    cached = _admin_cache.get(user.id)

    if cached:
        cached_value, checked_at = cached

        if (
            now - checked_at
        ).total_seconds() < ADMIN_CACHE_SECONDS:
            return cached_value

    try:
        member = await context.bot.get_chat_member(
            GROUP_ID,
            user.id,
        )

        result = member.status in (
            "administrator",
            "creator",
        )

    except Exception:
        result = False

    _admin_cache[user.id] = (
        result,
        now,
    )

    return result


# ============================================================
# RULES
# ============================================================

RULES = f"""
📋 قوانين {GROUP_NAME}

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه بوضوح:
📍 من وين → إلى وين.

3️⃣ 🚕 الكابتن الجاهز يضغط زر «🚕 جاهز للمشوار».

4️⃣ 🚫 ممنوع كتابة كلمة «خاص» داخل القروب.

5️⃣ 💰 السعر والتفاهم بين العميل والكابتن بالخاص.

6️⃣ 🚫 يمنع السب والإساءة.

7️⃣ 🚫 يمنع نشر الإعلانات والروابط.

8️⃣ 🔄 الرسائل المحولة ممنوعة.

9️⃣ 📍 الكابتن يعلن موقعه مرة واحدة يوميًا.

🔟 🤝 الاحترام واجب على الجميع.

⚠️ نظام المخالفات:

🟡 المخالفة الأولى → تحذير.

🟠 المخالفة الثانية → تحذير.

🔴 المخالفة الثالثة → تحذير أخير.

🔇 المخالفة الرابعة → كتم 24 ساعة.

🚫 المخالفة الخامسة وما بعدها → كتم 24 ساعة.

📩 الإدارة:
@{ADMIN_USERNAME}
"""


# ============================================================
# WELCOME
# ============================================================

async def welcome(update, context):
    message = update.message

    if not message:
        return

    for member in message.new_chat_members or []:

        if member.is_bot:
            continue

        save_user(member)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🧑🏻‍💼 أنا عميل",
                    callback_data=f"role_customer:{member.id}",
                ),
                InlineKeyboardButton(
                    "🚕 أنا كابتن",
                    callback_data=f"role_driver:{member.id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القوانين",
                    callback_data="rules",
                ),
                InlineKeyboardButton(
                    "📩 الإدارة",
                    url=f"https://t.me/{ADMIN_USERNAME}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📝 الشكاوى والاقتراحات",
                    callback_data=f"complaint:{member.id}",
                ),
            ],
        ])

        await message.reply_text(
            f"👋 يا هلا {display_user(member)} 🌹\n\n"
            f"نورت {GROUP_NAME} 🚘\n\n"
            "اختار صفتك عشان البوت يعرف كيف يخدمك 👇\n\n"
            "🧑🏻‍💼 العميل: يطلب مشوار.\n"
            "🚕 الكابتن: يأخذ المشاوير.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )


# ============================================================
# COMMANDS
# ============================================================

async def start(update, context):
    if not update.message:
        return

    await update.message.reply_text(
        f"🚘 أهلاً بك في {GROUP_NAME}\n\n"
        "🤖 البوت يعمل بنجاح ✅\n\n"
        "📋 /rules — القوانين\n"
        "ℹ️ /help — المساعدة"
    )


async def rules(update, context):
    if not update.message:
        return

    await update.message.reply_text(RULES)


async def help_command(update, context):
    if not update.message:
        return

    await update.message.reply_text(
        "🤖 طريقة استخدام القروب:\n\n"
        "🧑🏻‍💼 العميل:\n"
        "اكتب طلبك بطريقتك الطبيعية، مثل:\n"
        "ابغى أحد يوديني من الحمدانية للمطار.\n\n"
        "🚕 الكابتن:\n"
        "إذا يناسبك الطلب اضغط «جاهز للمشوار».\n\n"
        "📍 الكابتن يقدر يعلن موقعه مرة واحدة يوميًا."
    )


# ============================================================
# GREETINGS
# ============================================================

GREETINGS = [
    (
        [
            "السلام عليكم",
            "سلام عليكم",
            "السلام عليكم ورحمة الله",
            "السلام عليكم ورحمه الله",
        ],
        [
            "وعليكم السلام ورحمة الله وبركاته 🌹🚘",
            "وعليكم السلام يا هلا والله 👋",
            "وعليكم السلام، نورت القروب 🌹🚘",
        ],
    ),
    (
        [
            "هلا",
            "هلا والله",
            "هلا وغلا",
            "يا هلا",
            "اهلا",
            "اهلين",
            "مرحبا",
            "مرحبتين",
        ],
        [
            "هلا وغلا 🌹🚘",
            "يا هلا والله 👋",
            "حياك الله ونورتنا 🌹",
        ],
    ),
    (
        [
            "صباح الخير",
            "صباحكم خير",
        ],
        [
            "صباح النور والرزق 🌹🚘",
            "صباحكم خير وبركة 🤲",
            "صباح الخير يا أهل المشاوير ☀️",
        ],
    ),
    (
        [
            "مساء الخير",
            "مساءكم خير",
        ],
        [
            "مساء النور والخير 🌙🌹",
            "الله يمسيكم بالخير والعافية 🚘",
            "مساءكم طيب يا جماعة الخير ❤️",
        ],
    ),
    (
        [
            "شكرا",
            "مشكور",
            "يعطيك العافيه",
            "الله يعطيك العافيه",
            "يعطيكم العافيه",
        ],
        [
            "العفو يا الغالي 🌹",
            "حاضرين وما سوينا إلا الواجب 🚘",
            "الله يعافيك ويسعدك ❤️",
        ],
    ),
]


def get_greeting(text):
    normalized = normalize_arabic(text)

    for phrases, responses in GREETINGS:
        for phrase in phrases:
            p = normalize_arabic(phrase)

            if normalized == p:
                return random.choice(responses)

            if normalized.startswith(p + " "):
                return random.choice(responses)

    return None


# ============================================================
# SMART DRIVER DETECTION
# ============================================================

DRIVER_IDENTITY_PHRASES = [
    "انا كابتن",
    "أنا كابتن",
    "انا سواق",
    "أنا سواق",
    "انا كابتن جديد",
    "انا سواق جديد",
    "كابتن جديد",
    "سواق جديد",
]

DRIVER_READY_PHRASES = [
    "جاهز",
    "جاهز للمشوار",
    "جاهز للمشاوير",
    "كابتن وجاهز",
    "كابتن جاهز",
    "جاهز لاي مشوار",
    "جاهز لأي مشوار",
    "متوفر للمشاوير",
    "متوفر لاي مشوار",
    "متوفر لأي مشوار",
    "متاح للمشاوير",
    "متاح لأي مشوار",
    "جاهز للطلبات",
]


def is_driver_identity(text):
    normalized = normalize_arabic(text)

    for phrase in DRIVER_IDENTITY_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    return False


def is_driver_ready(text):
    normalized = normalize_arabic(text)

    # "انا كابتن" وحدها ليست جاهزية
    if normalized in (
        "انا كابتن",
        "انا سواق",
        "كابتن جديد",
        "سواق جديد",
    ):
        return False

    for phrase in DRIVER_READY_PHRASES:
        if normalized == normalize_arabic(phrase):
            return True

    return False


# ============================================================
# DRIVER LOCATION
# ============================================================

LOCATION_PHRASES = [
    "متواجد في",
    "متواجد ب",
    "موجود في",
    "موجود ب",
    "انا في",
    "انا موجود في",
    "انا موجود ب",
    "انا متواجد في",
    "انا متواجد ب",
    "متواجد حاليا في",
    "متواجد حاليا ب",
    "موجود حاليا في",
    "موجود حاليا ب",
    "متوفر في",
    "متوفر ب",
    "متاح في",
    "متاح ب",
]

LOCATION_END_PHRASES = [
    "لاي مشوار",
    "لاي مشاوير",
    "للمشاوير",
    "لاي طلب",
    "للطلبات",
    "متوفر للمشاوير",
    "متوفر لاي مشوار",
    "متاح للمشاوير",
    "جاهز للمشاوير",
    "جاهز لاي مشوار",
]


def is_location(text):
    normalized = normalize_arabic(text)

    if any(
        normalize_arabic(phrase) in normalized
        for phrase in LOCATION_PHRASES
    ):
        return True

    # مثال:
    # الحمدانية متواجد
    # الحمدانية موجود
    # الحمدانية متوفر
    if re.search(
        r"(?:متواجد|موجود|متوفر|متاح)\s+(?:حاليا\s+)?(?:في|ب)\s+",
        normalized,
    ):
        return True

    # صيغ عكسية:
    # الحمدانية متواجد
    # الحمدانية موجود لأي مشوار
    if re.search(
        r".{2,40}\s+(?:متواجد|موجود|متوفر|متاح)(?:\s+.+)?$",
        normalized,
    ):
        if any(
            word in normalized
            for word in (
                "حي",
                "الحمدانيه",
                "الصفا",
                "النسيم",
                "الزهراء",
                "المرجان",
                "ابحر",
                "المدينه",
                "مكه",
                "جده",
            )
        ):
            return True

    return False


def looks_like_driver_location(text):
    if not text:
        return False

    normalized = normalize_arabic(text)

    if is_driver_identity(text):
        return False

    if is_location(text):
        return True

    for phrase in LOCATION_END_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    return False


def extract_location(text):
    normalized = clean_text(text)

    patterns = [
        r"(?:انا\s+)?(?:موجود|متواجد|متوفر|متاح)"
        r"(?:\s+حاليا)?\s+(?:في|ب)\s+(.+?)(?:\s+(?:لاي|لأي|للمشاوير|للمشوار).*)?$",

        r"(?:انا\s+)?(?:في|ب)\s+(.+?)(?:\s+(?:لاي|لأي|للمشاوير|للمشوار).*)?$",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE,
        )

        if match:
            location = match.group(1).strip()
            location = re.sub(
                r"\s+(?:لاي|لأي|للمشاوير|للمشوار).*$",
                "",
                location,
                flags=re.IGNORECASE,
            )
            return location.strip()

    return ""


# ============================================================
# TRIP DETECTION
# ============================================================

TRIP_PHRASES = [
    "ابغى مشوار",
    "ابغا مشوار",
    "ابي مشوار",
    "ابغى توصيل",
    "ابغا توصيل",
    "ابي توصيل",
    "احتاج مشوار",
    "احتاج توصيل",
    "محتاج مشوار",
    "محتاج توصيل",
    "احد يوصلني",
    "مين يوصلني",
    "مين يوديني",
    "من يوصلني",
    "من يوديني",
    "احد يوديني",
    "ابغى اروح",
    "ابغا اروح",
    "ابي اروح",
    "ودي اروح",
    "ودي اروح من",
    "ممكن توصيل",
    "ممكن مشوار",
    "فيه كابتن",
    "في كابتن",
    "احد رايح",
    "كابتن يوديني",
    "عندي مشوار",
    "مشوار من",
    "توصيل من",
    "احتاج احد",
    "ابغى احد",
    "ابي احد",
    "محتاج احد",
    "مين عنده مشوار",
    "مين يقدر يوديني",
    "احد يقدر يوديني",
]


def has_route_structure(text):
    normalized = normalize_arabic(text)

    if "→" in text or "->" in text:
        return True

    if re.search(
        r"\bمن\s+.+?\s+(?:الى|الي|إلى|إلي|ل)\s+.+",
        normalized,
    ):
        return True

    return False


def looks_like_trip(text):
    if not text:
        return False

    normalized = normalize_arabic(text)

    # حماية قوية: رسائل الكابتن لا تصبح طلبات
    if looks_like_driver_location(text):
        return False

    if is_driver_identity(text):
        return False

    # طلب صريح
    for phrase in TRIP_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    # مسار واضح
    if has_route_structure(text):
        request_words = [
            "ابغى",
            "ابغا",
            "ابي",
            "احتاج",
            "محتاج",
            "مشوار",
            "توصيل",
            "يوصلني",
            "يوديني",
            "رايح",
            "اروح",
            "احد",
            "كابتن",
        ]

        if any(word in normalized for word in request_words):
            return True

    # صيغ:
    # الحمدانية للصفا
    # من الحمدانية للمطار
    if re.search(
        r".{2,40}\s+(?:لل|للم|الى|الي)\s+.{2,40}",
        normalized,
    ):
        if any(
            word in normalized
            for word in (
                "مشوار",
                "توصيل",
                "ابغى",
                "ابغا",
                "ابي",
                "احتاج",
                "محتاج",
                "احد",
                "كابتن",
            )
        ):
            return True

    return False


# ============================================================
# ROUTE EXTRACTION
# ============================================================

def clean_route_part(value):
    value = clean_text(value)

    value = re.sub(
        r"^(?:ابغى|ابغا|ابي|احتاج|محتاج|مشوار|توصيل|احد)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(
        r"\s+(?:بعد شوي|بعد قليل|الحين|الان|اليوم|بكره|بكرا).*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return value.strip(" .،,؛;:-")


def extract_route(text):
    original = clean_text(text)

    patterns = [
        r"من\s+(.+?)\s+(?:الى|إلى|الي|إلي)\s+(.+)",
        r"من\s+(.+?)\s+(?:ل|لل|للم)\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            original,
            re.IGNORECASE,
        )

        if match:
            start = clean_route_part(match.group(1))
            destination = clean_route_part(match.group(2))

            if len(start) >= 2 and len(destination) >= 2:
                return start, destination

    for separator in [
        "→",
        "->",
        "➜",
        "➡️",
    ]:
        if separator not in original:
            continue

        parts = original.split(separator, 1)

        if len(parts) == 2:
            start = clean_route_part(parts[0])
            destination = clean_route_part(parts[1])

            if len(start) >= 2 and len(destination) >= 2:
                return start, destination

    # صيغة:
    # الحمدانية للصفا
    match = re.search(
        r"^(.{2,50}?)\s+(?:لل|للم|ل)\s+(.{2,50})$",
        original,
        re.IGNORECASE,
    )

    if match:
        start = clean_route_part(match.group(1))
        destination = clean_route_part(match.group(2))

        if len(start) >= 2 and len(destination) >= 2:
            return start, destination

    return None, None


# ============================================================
# SMART INTENT ENGINE
# ============================================================

INTENT_DRIVER_IDENTITY = "driver_identity"
INTENT_DRIVER_LOCATION = "driver_location"
INTENT_DRIVER_READY = "driver_ready"
INTENT_TRIP_REQUEST = "trip_request"
INTENT_GREETING = "greeting"
INTENT_THANKS = "thanks"
INTENT_NORMAL = "normal"


def classify_message(user, text):
    """
    محرك فهم محلي بدون API خارجي.
    يعتمد على:
    - هوية العضو المحفوظة
    - شكل الرسالة
    - سياق الرسائل السابقة
    - عبارات النية
    """

    normalized = normalize_arabic(text)

    saved_driver = is_driver(user.id)
    saved_customer = is_customer(user.id)

    # --------------------------------------------------------
    # 1. تعريف الكابتن
    # --------------------------------------------------------

    if is_driver_identity(text):
        return INTENT_DRIVER_IDENTITY

    # --------------------------------------------------------
    # 2. تواجد الكابتن
    # --------------------------------------------------------

    if looks_like_driver_location(text):
        return INTENT_DRIVER_LOCATION

    # --------------------------------------------------------
    # 3. الجاهزية
    # --------------------------------------------------------

    if is_driver_ready(text):
        return INTENT_DRIVER_READY

    # --------------------------------------------------------
    # 4. طلب مشوار
    # --------------------------------------------------------

    if looks_like_trip(text):
        return INTENT_TRIP_REQUEST

    # --------------------------------------------------------
    # 5. تحية / شكر
    # --------------------------------------------------------

    greeting = get_greeting(text)

    if greeting:
        return INTENT_GREETING

    if normalized in (
        "شكرا",
        "مشكور",
        "مشكوره",
        "يعطيك العافيه",
        "الله يعطيك العافيه",
        "تسلم",
        "تسلم يالغالي",
    ):
        return INTENT_THANKS

    # --------------------------------------------------------
    # 6. لو كان مسجل كابتن، لا نفترض أن كل كلامه عميل
    # --------------------------------------------------------

    if saved_driver:
        if any(
            word in normalized
            for word in (
                "متواجد",
                "موجود",
                "متوفر",
                "متاح",
                "جاهز",
            )
        ):
            return INTENT_DRIVER_LOCATION

    # --------------------------------------------------------
    # 7. العميل المسجل + صياغة طلب
    # --------------------------------------------------------

    if saved_customer:
        if any(
            word in normalized
            for word in (
                "ابغى",
                "ابغا",
                "ابي",
                "احتاج",
                "محتاج",
                "احد يوديني",
                "احد يوصلني",
            )
        ):
            return INTENT_TRIP_REQUEST

    return INTENT_NORMAL


# ============================================================
# TRIP CREATION
# ============================================================

async def create_trip(message, context):
    customer = message.from_user

    if not customer:
        return

    text = clean_text(
        message.text or ""
    )

    start, destination = extract_route(text)

    if start and destination:
        route = (
            f"📍 <b>من:</b> {html(start)}\n"
            f"🏁 <b>إلى:</b> {html(destination)}"
        )
    else:
        route = (
            "📍 <b>تفاصيل المشوار:</b>\n"
            f"{html(text)}"
        )

    sent = await message.reply_text(
        "🚘 <b>╭━━ بطاقة مشوار ━━╮</b>\n\n"
        "🧑🏻‍💼 <b>عميل يطلب مشوار</b>\n\n"
        f"{route}\n\n"
        "👨‍✈️ الكابتن المناسب يضغط «جاهز للمشوار».\n"
        "💰 السعر والتفاهم يكون بالخاص.\n\n"
        "🚕 <b>╰━━━━━━━━━━━━╯</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🚕 جاهز للمشوار",
                    callback_data="ready:0",
                )
            ],
            [
                InlineKeyboardButton(
                    "📝 شكوى / اقتراح",
                    callback_data=f"complaint:{customer.id}",
                )
            ],
        ]),
    )

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            INSERT OR REPLACE INTO trips (
                message_id,
                customer_id,
                customer_username,
                created_at,
                start,
                destination,
                original_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sent.message_id,
            customer.id,
            customer.username or "",
            datetime.now(SAUDI_TZ).isoformat(),
            start or "",
            destination or "",
            text,
        ))

        con.commit()

    await sent.edit_reply_markup(
        InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🚕 جاهز للمشوار",
                    callback_data=f"ready:{sent.message_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "📝 شكوى / اقتراح",
                    callback_data=f"complaint:{customer.id}",
                )
            ],
        ])
    )


# ============================================================
# DRIVER LOCATION HANDLER
# ============================================================

async def handle_location(update, context):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    text = clean_text(message.text or "")

    if not text:
        return False

    if not looks_like_driver_location(text):
        return False

    # ========================================================
    # إذا مسجل كابتن نعتمد على التسجيل مباشرة
    # ========================================================

    driver_registered = is_driver(user.id)

    if not driver_registered:

        # إذا الإعلان واضح جدًا، التسجيل تلقائي
        strong_driver_signals = [
            "لاي مشوار",
            "لأي مشوار",
            "للمشاوير",
            "متوفر للمشاوير",
            "متوفر لأي مشوار",
            "جاهز للمشاوير",
            "جاهز لأي مشوار",
        ]

        normalized = normalize_arabic(text)

        if any(
            normalize_arabic(p) in normalized
            for p in strong_driver_signals
        ):
            mark_driver(user)
            driver_registered = True

    if not driver_registered:

        await message.reply_text(
            "📍 واضح إن رسالتك إعلان تواجد كابتن 🚕\n\n"
            "إذا أنت كابتن اضغط «🚕 أنا كابتن» مرة واحدة، "
            "وبعدها البوت بيتعرف عليك تلقائيًا.\n\n"
            "وإذا كنت تقصد طلب مشوار، اكتب لي من وين إلى وين."
        )

        save_context(
            user.id,
            text,
            INTENT_DRIVER_LOCATION,
        )

        return True

    today = datetime.now(
        SAUDI_TZ
    ).date().isoformat()

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT last_date
            FROM locations
            WHERE user_id = ?
        """, (user.id,))

        row = cur.fetchone()

        if row and row[0] == today:
            already = True
        else:
            already = False

            cur.execute("""
                INSERT OR REPLACE INTO locations (
                    user_id,
                    last_date
                )
                VALUES (?, ?)
            """, (
                user.id,
                today,
            ))

            con.commit()

    save_context(
        user.id,
        text,
        INTENT_DRIVER_LOCATION,
    )

    if already:
        await message.reply_text(
            "😂 عرفنا وينك اليوم.\n\n"
            "📍 إعلان التواجد مسموح مرة واحدة فقط باليوم."
        )

        return True

    location = extract_location(text)

    location_text = (
        html(location)
        if location
        else html(text)
    )

    await message.reply_text(
        f"📍 <b>تم تسجيل تواجد الكابتن</b>\n\n"
        f"{display_user(user)}\n\n"
        f"📌 {location_text}\n\n"
        "🚕 تم تسجيل موقعك، الله يرزقك مشوار طيب.",
        parse_mode=ParseMode.HTML,
    )

    return True


# ============================================================
# READY BUTTON
# ============================================================

async def ready_button(update, context):
    query = update.callback_query
    driver = query.from_user

    if not driver:
        await query.answer()
        return

    try:
        trip_id = int(
            query.data.split(":")[1]
        )
    except Exception:
        await query.answer(
            "حدث خطأ في الطلب.",
            show_alert=True,
        )
        return

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT
                customer_id,
                customer_username,
                start,
                destination
            FROM trips
            WHERE message_id = ?
        """, (trip_id,))

        trip = cur.fetchone()

    if not trip:
        await query.answer(
            "الطلب غير موجود.",
            show_alert=True,
        )
        return

    customer_id = trip[0]
    start = trip[2]
    destination = trip[3]

    # تسجيله ككابتن فقط إذا ضغط زر المشوار
    if not is_driver(driver.id):
        mark_driver(driver)

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT 1
            FROM ready
            WHERE trip_id = ?
            AND driver_id = ?
        """, (
            trip_id,
            driver.id,
        ))

        already_ready = cur.fetchone()

        if already_ready:
            await query.answer(
                "أنت مسجل لهذا المشوار بالفعل ✅",
                show_alert=True,
            )
            return

        cur.execute("""
            INSERT INTO ready (
                trip_id,
                driver_id
            )
            VALUES (?, ?)
        """, (
            trip_id,
            driver.id,
        ))

        con.commit()

    save_context(
        driver.id,
        "جاهز للمشوار",
        INTENT_DRIVER_READY,
    )

    await query.answer(
        random.choice(READY_MESSAGES),
        show_alert=True,
    )

    route = ""

    if start and destination:
        route = (
            f"\n📍 {html(start)}"
            f" → {html(destination)}"
        )

    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                "🚕 <b>كابتن جاهز للمشوار</b>\n\n"
                f"👨‍✈️ {display_user(driver)}"
                f"{route}\n\n"
                "💰 التفاهم والسعر بالخاص."
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "📩 تواصل مع العميل",
                        callback_data=f"contact:{trip_id}:{driver.id}",
                    ),
                    InlineKeyboardButton(
                        "📞 تواصل مع الكابتن",
                        callback_data=f"contactdriver:{customer_id}:{driver.id}",
                    ),
                ]
            ]),
            reply_to_message_id=trip_id,
        )

    except Exception as error:
        logger.error(
            "Ready notification error: %s",
            error,
        )


# ============================================================
# CONTACT CUSTOMER
# ============================================================

async def contact_customer_button(update, context):
    query = update.callback_query
    user = query.from_user

    if not user:
        await query.answer()
        return

    try:
        _, trip_id, driver_id = query.data.split(":")
        trip_id = int(trip_id)
        driver_id = int(driver_id)
    except Exception:
        await query.answer()
        return

    if user.id != driver_id:
        await query.answer(
            "😂 العب غيرها ياحلو، هذا الزر للكابتن اللي ضغط جاهز فقط.",
            show_alert=True,
        )
        return

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT customer_id, customer_username
            FROM trips
            WHERE message_id = ?
        """, (trip_id,))

        row = cur.fetchone()

    if not row:
        await query.answer(
            "الطلب غير موجود.",
            show_alert=True,
        )
        return

    customer_id = row[0]
    username = row[1] or ""

    if username:
        await query.answer(
            f"تم فتح تواصل العميل: @{username}",
            show_alert=True,
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "📩 <b>بيانات العميل</b>\n\n"
                f"👤 @{html(username)}\n\n"
                "تواصل معه بخصوص المشوار 🚘"
            ),
            parse_mode=ParseMode.HTML,
        )
    else:
        await query.answer(
            "العميل لا يملك يوزر تيليجرام.",
            show_alert=True,
        )


# ============================================================
# CONTACT DRIVER
# ============================================================

async def contact_driver_button(update, context):
    query = update.callback_query
    user = query.from_user

    if not user:
        await query.answer()
        return

    try:
        _, customer_id, driver_id = query.data.split(":")
        customer_id = int(customer_id)
        driver_id = int(driver_id)
    except Exception:
        await query.answer()
        return

    if user.id != customer_id:
        await query.answer(
            "هذا الزر مخصص لصاحب الطلب فقط 🙏",
            show_alert=True,
        )
        return

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT 1
            FROM ready
            WHERE driver_id = ?
            AND trip_id IN (
                SELECT message_id
                FROM trips
                WHERE customer_id = ?
            )
        """, (
            driver_id,
            customer_id,
        ))

        row = cur.fetchone()

    if not row:
        await query.answer(
            "الكابتن غير مسجل لهذا الطلب.",
            show_alert=True,
        )
        return

    username = get_username(driver_id)

    if not username:
        await query.answer(
            "الكابتن لا يملك يوزر.",
            show_alert=True,
        )
        return

    await query.answer(
        f"تم فتح تواصل الكابتن: @{username}",
        show_alert=True,
    )

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "📞 <b>بيانات الكابتن</b>\n\n"
            f"🚕 @{html(username)}\n\n"
            "الله يوفقكم ويتمم المشوار على خير 🌹"
        ),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# ROLE BUTTONS
# ============================================================

async def role_selection_button(update, context):
    query = update.callback_query
    data = query.data or ""
    clicked_by = query.from_user

    if not clicked_by:
        await query.answer()
        return

    try:
        role, target_id = data.split(":", 1)
        target_id = int(target_id)
    except Exception:
        await query.answer()
        return

    admin = await is_admin(
        update,
        context,
    )

    if clicked_by.id != target_id and not admin:
        await query.answer(
            "هذا الزر مخصص للعضو الجديد أو للمسؤول فقط 🙏",
            show_alert=True,
        )
        return

    if clicked_by.id == target_id:
        save_user(clicked_by)
    else:
        row = get_user_info(target_id)

        if not row:
            await query.answer(
                "لم يتم العثور على بيانات العضو.",
                show_alert=True,
            )
            return

    if role == "role_driver":
        mark_driver_by_id(target_id)

        await query.answer(
            "تم تسجيلك ككابتن 🚕 وسيتم التعرف عليك تلقائيًا.",
            show_alert=True,
        )

        target_display = display_saved_user(target_id)

        if clicked_by.id == target_id:
            text = (
                f"🚕 {target_display}\n\n"
                "تم تسجيلك ككابتن بنجاح ✅\n\n"
                "من الآن البوت يعرف أنك كابتن، "
                "وما تحتاج تضغط الزر مرة ثانية.\n\n"
                "إذا شفت مشوار يناسبك اضغط:\n"
                "🚕 جاهز للمشوار\n\n"
                "وإذا كنت متواجد في حي معين، "
                "اكتب مثلًا:\n"
                "📍 أنا موجود في الحمدانية لأي مشوار."
            )
        else:
            text = (
                "👑 <b>تم تعديل صفة العضو</b>\n\n"
                f"👤 العضو: {target_display}\n"
                "🚕 الصفة: <b>كابتن</b>\n\n"
                "تم حفظ التعديل بنجاح ✅"
            )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
        )

        return

    if role == "role_customer":
        mark_customer_by_id(target_id)

        await query.answer(
            "تم تسجيل العضو كعميل 🧑🏻‍💼",
            show_alert=True,
        )

        target_display = display_saved_user(target_id)

        if clicked_by.id == target_id:
            text = (
                f"🧑🏻‍💼 {target_display}\n\n"
                "أهلاً فيك 🌹\n\n"
                "لطلب مشوار اكتب بطريقتك الطبيعية، مثل:\n"
                "ابغى أحد يوديني من الحمدانية إلى المطار 🚘"
            )
        else:
            text = (
                "👑 <b>تم تعديل صفة العضو</b>\n\n"
                f"👤 العضو: {target_display}\n"
                "🧑🏻‍💼 الصفة: <b>عميل</b>\n\n"
                "تم حفظ التعديل بنجاح ✅"
            )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# COMPLAINTS
# ============================================================

async def complaint_button(update, context):
    query = update.callback_query
    user = query.from_user

    if not user:
        await query.answer()
        return

    await query.answer(
        "سيتم فتح التواصل مع الإدارة 📩"
    )

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "📝 <b>الشكاوى والاقتراحات</b>\n\n"
            "اكتب شكواك أو اقتراحك وأرسلها هنا.\n\n"
            f"📩 الإدارة: @{ADMIN_USERNAME}\n\n"
            "سيتم التعامل معها بسرية واحترام."
        ),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# LINKS / FORWARDS
# ============================================================

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
    re.IGNORECASE,
)


def _normalize_link(link):
    link = link.lower().rstrip("/")

    for prefix in (
        "https://",
        "http://",
    ):
        if link.startswith(prefix):
            link = link[len(prefix):]
            break

    if link.startswith("www."):
        link = link[4:]

    return link


_ALLOWED_LINK_NORMALIZED = _normalize_link(
    ALLOWED_GROUP_LINK
)


def forbidden_link(text):
    if not text:
        return False

    for link in URL_PATTERN.findall(text):
        link = link.rstrip(
            ".,!?؟،؛:)]}>\"'"
        )

        if _normalize_link(link).startswith(
            _ALLOWED_LINK_NORMALIZED
        ):
            continue

        return True

    return False


def is_forwarded(message):
    return bool(
        getattr(message, "forward_origin", None)
        or getattr(message, "forward_from", None)
        or getattr(message, "forward_from_chat", None)
        or getattr(message, "forward_sender_name", None)
    )


async def protect_message(update, context):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    if is_owner(user):
        return False

    if await is_admin(update, context):
        return False

    if is_forwarded(message):
        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {display_user(user)}\n\n"
            "الرسائل المحولة ممنوعة 🚫\n"
            "اكتب الرسالة مباشرة.",
            parse_mode=ParseMode.HTML,
        )

        return True

    text = (
        message.text
        or message.caption
        or ""
    )

    if forbidden_link(text):
        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {display_user(user)}\n\n"
            "الروابط ممنوعة في القروب 🚫",
            parse_mode=ParseMode.HTML,
        )

        return True

    return False


# ============================================================
# SMART VIOLATIONS
# ============================================================

BAD_WORDS = [
    "يا غبي",
    "يا حمار",
    "يا كلب",
    "يا تافه",
    "قليل الادب",
    "قليل الأدب",
    "انقلع",
]

INAPPROPRIATE = [
    "مين يبي يتعرف",
    "مين يبغى يتعرف",
    "ابغى بنت",
    "ابغى وحدة",
    "تعالي معي",
]


def normalized_has_word(normalized, phrase):
    return normalize_arabic(phrase) in normalized


def violation_reason(text):
    normalized = normalize_arabic(text)
    stripped = normalized.strip()

    # --------------------------------------------------------
    # خاص
    # --------------------------------------------------------

    if compact_arabic(text) in (
        "خاص",
        "الخاص",
    ):
        return "خاص"

    # --------------------------------------------------------
    # سب
    # --------------------------------------------------------

    for word in BAD_WORDS:
        if normalized_has_word(normalized, word):
            return "إساءة أو سب"

    # --------------------------------------------------------
    # كلام غير مناسب
    # --------------------------------------------------------

    for phrase in INAPPROPRIATE:
        if normalized_has_word(normalized, phrase):
            return "كلام غير مناسب"

    # --------------------------------------------------------
    # سعر مكتوب
    # --------------------------------------------------------

    if re.search(
        r"(?:السعر|بكم|كم|ريال|الاجره|الاجره|التكلفه|المبلغ)"
        r"\s*(?:هو|يعني|تقريبا)?\s*\d+",
        normalized,
    ):
        return "كتابة السعر في العام"

    if re.search(
        r"\d+\s*(?:ريال|ر\.?س)",
        normalized,
    ):
        return "كتابة السعر في العام"

    return None


async def handle_violation(update, context, reason):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return

    if is_owner(user):
        return

    if await is_admin(update, context):
        return

    if reason == "خاص":
        try:
            await message.delete()
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"⚠️ {display_user(user)}\n\n"
                "🚫 ممنوع كتابة «خاص» يا حلو.\n"
                "إذا أنت كابتن وجاهز للمشوار، "
                "اضغط زر «جاهز للمشوار» على بطاقة المشوار.\n\n"
                "📝 تم تسجيلها كمخالفة."
            ),
            parse_mode=ParseMode.HTML,
        )

        reason = "كتابة كلمة خاص"

    save_user(user)

    now = datetime.now(SAUDI_TZ)

    with db() as con:
        cur = con.cursor()

        cur.execute("""
            SELECT violations, last_violation_at
            FROM users
            WHERE user_id = ?
        """, (user.id,))

        row = cur.fetchone()

        current = row[0] if row else 0
        last_at = row[1] if row else None

        if last_at:
            try:
                last_dt = datetime.fromisoformat(last_at)

                if (
                    now - last_dt
                ).days >= VIOLATION_RESET_DAYS:
                    current = 0

            except Exception:
                pass

        count = current + 1

        cur.execute("""
            UPDATE users
            SET violations = ?,
                last_violation_at = ?
            WHERE user_id = ?
        """, (
            count,
            now.isoformat(),
            user.id,
        ))

        con.commit()

    save_context(
        user.id,
        message.text or "",
        "violation",
    )

    try:
        await message.delete()
    except Exception:
        pass

    if count >= 4:
        try:
            until = (
                datetime.now(SAUDI_TZ)
                + timedelta(hours=MUTE_HOURS)
            )

            await context.bot.restrict_chat_member(
                GROUP_ID,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                    can_send_audios=False,
                    can_send_documents=False,
                    can_send_photos=False,
                    can_send_videos=False,
                    can_send_video_notes=False,
                    can_send_voice_notes=False,
                    can_send_polls=False,
                    can_send_other_messages=False,
                    can_add_web_page_previews=False,
                    can_change_info=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                ),
                until_date=until,
            )

            await context.bot.send_message(
                GROUP_ID,
                (
                    f"🔇 <b>تم كتم العضو</b>\n\n"
                    f"{display_user(user)}\n\n"
                    f"🔴 المخالفة رقم <b>{count}</b>\n"
                    "⏱ مدة الكتم: <b>24 ساعة</b>"
                ),
                parse_mode=ParseMode.HTML,
            )

        except Exception as error:
            logger.error(
                "Mute error: %s",
                error,
            )

        return

    if count == 3:
        await context.bot.send_message(
            GROUP_ID,
            (
                "🔴 <b>المخالفة الثالثة</b>\n\n"
                f"{display_user(user)}\n\n"
                "⚠️ هذه آخر مخالفة قبل الكتم.\n"
                "أي مخالفة جديدة = 🔇 كتم 24 ساعة."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    if count == 2:
        await context.bot.send_message(
            GROUP_ID,
            (
                "🟠 <b>المخالفة الثانية</b>\n\n"
                f"{display_user(user)}\n\n"
                f"السبب: {html(reason)}\n"
                "⚠️ انتبه، المخالفة القادمة قد تؤدي للكتم."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    await context.bot.send_message(
        GROUP_ID,
        (
            "🟡 <b>تنبيه للمرة الأولى</b>\n\n"
            f"{display_user(user)}\n\n"
            f"السبب: {html(reason)}\n"
            "المخالفات: 🟡 1 / 3"
        ),
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# CHAT RESPONSE
# ============================================================

async def handle_chat_response(message):
    text = message.text or ""

    response = get_greeting(text)

    if not response:
        return False

    if looks_like_trip(text):
        return False

    if looks_like_driver_location(text):
        return False

    await message.reply_text(response)

    return True


# ============================================================
# SMART MESSAGE HANDLER
# ============================================================

async def message_handler(update, context):
    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    save_user(user)

    # --------------------------------------------------------
    # حماية الرسائل
    # --------------------------------------------------------

    if await protect_message(update, context):
        return

    text = clean_text(
        message.text or ""
    )

    if not text:
        return

    # --------------------------------------------------------
    # المخالفات
    # --------------------------------------------------------

    reason = violation_reason(text)

    if reason:
        await handle_violation(
            update,
            context,
            reason,
        )
        return

    # --------------------------------------------------------
    # التصنيف الذكي
    # --------------------------------------------------------

    intent = classify_message(
        user,
        text,
    )

    logger.info(
        "SMART INTENT | user=%s | driver=%s | customer=%s | intent=%s | text=%s",
        user.id,
        is_driver(user.id),
        is_customer(user.id),
        intent,
        text[:100],
    )

    # --------------------------------------------------------
    # تعريف كابتن
    # --------------------------------------------------------

    if intent == INTENT_DRIVER_IDENTITY:
        mark_driver(user)

        save_context(
            user.id,
            text,
            INTENT_DRIVER_IDENTITY,
        )

        await message.reply_text(
            f"🚕 {display_user(user)}\n\n"
            "تم التعرف عليك ككابتن وحفظ صفتك ✅\n\n"
            "من الآن ما تحتاج تكتب «أنا كابتن» مرة ثانية.\n"
            "إذا كنت متواجد في منطقة، اكتب مثلًا:\n"
            "📍 أنا موجود في الحمدانية لأي مشوار.\n\n"
            "وإذا شفت بطاقة مشوار تناسبك اضغط:\n"
            "🚕 جاهز للمشوار",
            parse_mode=ParseMode.HTML,
        )

        return

    # --------------------------------------------------------
    # تواجد الكابتن
    # --------------------------------------------------------

    if intent == INTENT_DRIVER_LOCATION:
        await handle_location(
            update,
            context,
        )
        return

    # --------------------------------------------------------
    # جاهزية عامة
    # --------------------------------------------------------

    if intent == INTENT_DRIVER_READY:
        mark_driver(user)

        save_context(
            user.id,
            text,
            INTENT_DRIVER_READY,
        )

        await message.reply_text(
            f"🚕 {display_user(user)}\n\n"
            "تم تسجيلك ككابتن جاهز ✅\n"
            "والبوت يعرف أنك كابتن الآن.\n\n"
            "إذا تقصد مشوارًا معينًا، استخدم زر "
            "«جاهز للمشوار» الموجود على بطاقة المشوار.\n\n"
            "الله يرزقك ويرافقك السلامة 🌹",
            parse_mode=ParseMode.HTML,
        )

        return

    # --------------------------------------------------------
    # طلب مشوار
    # --------------------------------------------------------

    if intent == INTENT_TRIP_REQUEST:
        mark_customer(user)

        save_context(
            user.id,
            text,
            INTENT_TRIP_REQUEST,
        )

        await create_trip(
            message,
            context,
        )

        return

    # --------------------------------------------------------
    # تحية
    # --------------------------------------------------------

    if intent == INTENT_GREETING:
        save_context(
            user.id,
            text,
            INTENT_GREETING,
        )

        await handle_chat_response(
            message
        )

        return

    # --------------------------------------------------------
    # طبيعي
    # --------------------------------------------------------

    save_context(
        user.id,
        text,
        INTENT_NORMAL,
    )

    # ردود المحادثة العادية
    await handle_chat_response(
        message
    )


# ============================================================
# REMINDER
# ============================================================

async def interactive_reminder(context):
    text = random.choice(
        INTERACTIVE_REMINDERS
    ).format(
        GROUP_NAME=GROUP_NAME,
        ALLOWED_GROUP_LINK=ALLOWED_GROUP_LINK,
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📤 نشر رابط القروب",
                url=(
                    "https://t.me/share/url"
                    f"?url={ALLOWED_GROUP_LINK}"
                    "&text=🚘 انضموا لقروب مشاوير جدة"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 القوانين",
                callback_data="rules",
            ),
            InlineKeyboardButton(
                "🚘 فتح القروب",
                url=ALLOWED_GROUP_LINK,
            ),
        ],
    ])

    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

        logger.info(
            "Interactive reminder sent successfully."
        )

    except Exception as error:
        logger.error(
            "Reminder error: %s",
            error,
        )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(update, context):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    if data == "rules":
        await query.answer()

        await query.message.reply_text(
            RULES
        )

        return

    if data.startswith("ready:"):
        await ready_button(
            update,
            context,
        )
        return

    if (
        data.startswith("role_customer:")
        or data.startswith("role_driver:")
    ):
        await role_selection_button(
            update,
            context,
        )
        return

    if data.startswith("contact:"):
        await contact_customer_button(
            update,
            context,
        )
        return

    if data.startswith("contactdriver:"):
        await contact_driver_button(
            update,
            context,
        )
        return

    if data.startswith("complaint:"):
        await complaint_button(
            update,
            context,
        )
        return

    await query.answer()


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update, context):
    logger.error(
        "BOT ERROR: %s",
        context.error,
        exc_info=True,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "====================================",
        flush=True,
    )

    print(
        "🚘 Starting Smart Mishawir Jeddah Bot...",
        flush=True,
    )

    print(
        "====================================",
        flush=True,
    )

    init_db()

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.job_queue.run_repeating(
        interactive_reminder,
        interval=REMINDER_INTERVAL,
        first=REMINDER_INTERVAL,
        name="interactive_group_reminder",
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "rules",
            rules,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "✅ Smart bot is running...",
        flush=True,
    )

    print(
        "🧠 Smart intent engine: ENABLED",
        flush=True,
    )

    print(
        "👤 Persistent roles: ENABLED",
        flush=True,
    )

    print(
        "💾 Context memory: ENABLED",
        flush=True,
    )

    print(
        "📢 Interactive reminders: every 30 minutes",
        flush=True,
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
