import os
import re
import sqlite3
import logging
import random
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

OWNER_ID = 952638746

ALLOWED_GROUP_LINK = "https://t.me/JeddahRides"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

MUTE_HOURS = 24
VIOLATION_RESET_DAYS = 30
ADMIN_CACHE_SECONDS = 300

REMINDER_INTERVAL = 30 * 60


# ============================================================
# 🏷️ وسوم الأعضاء
# ============================================================

DRIVER_BADGE = "𓆩🚘𓆪 كابتن"
CUSTOMER_BADGE = "𓆩👤𓆪 عميل"


# ============================================================
# التذكيرات
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
                last_violation_at TEXT
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

        cur.execute("PRAGMA table_info(users)")

        columns = [
            row[1]
            for row in cur.fetchall()
        ]

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

        cur.execute("PRAGMA table_info(trips)")

        trip_columns = [
            row[1]
            for row in cur.fetchall()
        ]

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

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            INSERT INTO users (
                user_id,
                name,
                username
            )
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


def mark_driver(user):

    save_user(user)

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            UPDATE users
            SET is_driver = 1,
                is_customer = 0
            WHERE user_id = ?
        """, (user.id,))

        con.commit()


def mark_customer(user):

    save_user(user)

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            UPDATE users
            SET is_customer = 1,
                is_driver = 0
            WHERE user_id = ?
        """, (user.id,))

        con.commit()


def mark_driver_by_id(user_id):

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            UPDATE users
            SET is_driver = 1,
                is_customer = 0
            WHERE user_id = ?
        """, (user_id,))

        con.commit()


def mark_customer_by_id(user_id):

    with db() as con:

        cur = con.cursor()

        cur.execute("""
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
            SELECT user_id, name, username
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

    return bool(
        row and row[0] == 1
    )


def is_customer(user_id):

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            SELECT is_customer
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = cur.fetchone()

    return bool(
        row and row[0] == 1
    )


def get_username(user_id):

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            SELECT username
            FROM users
            WHERE user_id = ?
        """, (user_id,))

        row = cur.fetchone()

    return (
        row[0]
        if row and row[0]
        else ""
    )


# ============================================================
# 🏷️ تحديد الوسم
# ============================================================

def get_role_badge(user_id):

    if is_driver(user_id):
        return DRIVER_BADGE

    if is_customer(user_id):
        return CUSTOMER_BADGE

    return ""


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

    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_arabic(text):

    text = clean_text(
        text
    ).lower()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new,
        )

    return text


# ============================================================
# عرض اسم العضو
# ============================================================

def display_user(user):

    if not user:
        return "عضو"

    name = html(
        user.full_name
    )

    badge = get_role_badge(
        user.id
    )

    if badge:

        return (
            f"<b>{html(badge)} "
            f"{name}</b>"
        )

    return f"<b>{name}</b>"


def display_saved_user(user_id):

    row = get_user_info(
        user_id
    )

    if not row:
        return "العضو"

    _, name, _ = row

    badge = get_role_badge(
        user_id
    )

    if badge:

        return (
            f"<b>{html(badge)} "
            f"{html(name or 'عضو')}</b>"
        )

    return (
        f"<b>{html(name or 'عضو')}</b>"
    )


# ============================================================
# ADMIN
# ============================================================

_admin_cache = {}


def is_owner(user):

    if not user:
        return False

    if user.id == OWNER_ID:
        return True

    if user.username:

        return (
            user.username.lower()
            == OWNER_USERNAME.lower()
        )

    return False


async def is_admin(
    update,
    context,
):

    user = update.effective_user

    if not user:
        return False

    if is_owner(user):
        return True

    now = datetime.now(
        SAUDI_TZ
    )

    cached = _admin_cache.get(
        user.id
    )

    if cached:

        cached_value, checked_at = cached

        if (
            now - checked_at
        ).total_seconds()
        < ADMIN_CACHE_SECONDS:

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

2️⃣ العميل يكتب طلبه مباشرة في القروب:
📍 من وين → إلى وين.

3️⃣ 🚕 الكابتن إذا كان مهتم بالمشوار يرد على رسالة العميل نفسها ويكتب:
«جاهز»

4️⃣ 💰 السعر والتفاهم بين العميل والكابتن بالخاص.

5️⃣ 🚫 ممنوع كتابة كلمة «خاص» داخل القروب.

6️⃣ 🚫 يمنع السب والإساءة.

7️⃣ 🚫 يمنع نشر الإعلانات والروابط غير المسموحة.

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

async def welcome(
    update,
    context,
):

    message = update.message

    if not message:
        return

    for member in (
        message.new_chat_members or []
    ):

        if member.is_bot:
            continue

        save_user(member)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🧑🏻‍💼 أنا عميل",
                    callback_data=(
                        f"role_customer:{member.id}"
                    ),
                ),
                InlineKeyboardButton(
                    "🚕 أنا كابتن",
                    callback_data=(
                        f"role_driver:{member.id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "📋 القوانين",
                    callback_data="rules",
                ),
                InlineKeyboardButton(
                    "📩 الإدارة",
                    url=(
                        f"https://t.me/{ADMIN_USERNAME}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "📝 الشكاوى والاقتراحات",
                    callback_data=(
                        f"complaint:{member.id}"
                    ),
                ),
            ],
        ])

        await message.reply_text(

            f"👋 يا هلا {display_user(member)} 🌹\n\n"
            f"نورت {GROUP_NAME} 🚘\n\n"

            "🧑🏻‍💼 <b>إذا كنت عميل:</b>\n"
            "اضغط «أنا عميل» مرة واحدة، وبعدها اكتب مشوارك مباشرة في القروب.\n\n"

            "مثال:\n"
            "السلام عليكم، أبغى مشوار من الحمدانية إلى المطار الساعة 5.\n\n"

            "🚕 <b>إذا كنت كابتن:</b>\n"
            "اضغط «أنا كابتن» مرة واحدة فقط.\n"
            "إذا شفت طلب يناسبك، <b>رد على رسالة العميل نفسها واكتب «جاهز».</b>\n\n"

            "🤖 البوت بعدها يرسل لك كرت التواصل مع العميل.\n"
            "ولا تحتاج تسجل نفسك ككابتن كل مرة.",

            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )


# ============================================================
# MEMBER LEFT
# ============================================================

async def member_left_handler(
    update,
    context,
):

    message = update.message

    if not message:
        return

    left_member = (
        message.left_chat_member
    )

    if not left_member:
        return

    if left_member.is_bot:
        return

    save_user(left_member)

    try:

        member = await context.bot.get_chat_member(
            GROUP_ID,
            left_member.id,
        )

        if member.status == "kicked":

            action_text = (
                "🚫 تم إخراجه من القروب"
            )

        else:

            action_text = (
                "👋 غادر القروب"
            )

    except Exception:

        action_text = (
            "👋 غادر القروب"
        )

    username_text = ""

    if left_member.username:

        username_text = (
            f"\n🔹 <b>اليوزر:</b> "
            f"@{html(left_member.username)}"
        )

    badge = get_role_badge(
        left_member.id
    )

    badge_text = ""

    if badge:

        badge_text = (
            f"\n🏷️ <b>الصفة:</b> "
            f"{html(badge)}"
        )

    try:

        await context.bot.send_message(

            chat_id=OWNER_ID,

            text=(
                "🚨 <b>تنبيه مغادرة عضو</b>\n\n"

                f"👤 <b>الاسم:</b> "
                f"{html(left_member.full_name)}"

                f"{username_text}"

                f"{badge_text}\n"

                f"🆔 <b>ID:</b> "
                f"<code>{left_member.id}</code>\n\n"

                f"{action_text}\n"

                f"📍 <b>القروب:</b> "
                f"{html(GROUP_NAME)}"
            ),

            parse_mode=ParseMode.HTML,
        )

    except Exception as error:

        logger.error(
            "Failed to send member-left notification: %s",
            error,
        )


# ============================================================
# COMMANDS
# ============================================================

async def start(
    update,
    context,
):

    if not update.message:
        return

    await update.message.reply_text(

        f"🚘 أهلاً بك في {GROUP_NAME}\n\n"

        "🤖 البوت يعمل بنجاح ✅\n\n"

        "📋 /rules — القوانين\n"
        "ℹ️ /help — المساعدة"
    )


async def rules(
    update,
    context,
):

    if not update.message:
        return

    await update.message.reply_text(
        RULES
    )


async def help_command(
    update,
    context,
):

    if not update.message:
        return

    await update.message.reply_text(

        "🤖 طريقة استخدام القروب:\n\n"

        "🧑🏻‍💼 العميل:\n"
        "اضغط «أنا عميل» مرة واحدة عند الترحيب، "
        "ثم اكتب طلب المشوار مباشرة.\n\n"

        "مثال:\n"
        "السلام عليكم، أبغى مشوار من الحمدانية إلى المطار.\n\n"

        "🚕 الكابتن:\n"
        "اضغط «أنا كابتن» مرة واحدة.\n"
        "إذا وجدت طلبًا مناسبًا، "
        "رد على رسالة العميل نفسها واكتب «جاهز».\n\n"

        "🤖 بعدها يظهر كرت صغير للتواصل."
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
            "أهلين",
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
        ],
        [
            "العفو يا الغالي 🌹",
            "حاضرين وما سوينا إلا الواجب 🚘",
            "الله يعافيك ويسعدك ❤️",
        ],
    ),
]


def get_greeting(text):

    normalized = normalize_arabic(
        text
    )

    for phrases, responses in GREETINGS:

        for phrase in phrases:

            p = normalize_arabic(
                phrase
            )

            if normalized.startswith(p):

                return random.choice(
                    responses
                )

    return None


# ============================================================
# DRIVER READY
# ============================================================

DRIVER_READY_PHRASES = [
    "جاهز",
    "جاهز للمشوار",
    "جاهز للمشاوير",
    "كابتن وجاهز",
    "كابتن جاهز",
    "انا كابتن",
    "انا كابتن وجاهز",
    "جاهز لاي مشوار",
    "جاهز لأي مشوار",
    "متوفر للمشاوير",
    "متوفر لاي مشوار",
    "متوفر لأي مشوار",
]


def is_driver_ready(text):

    normalized = normalize_arabic(
        text
    )

    phrases = [
        normalize_arabic(x)
        for x in DRIVER_READY_PHRASES
    ]

    return normalized in phrases


READY_MESSAGES = [

    "رافقتك السلامة يا كابتن 🚕🌹",

    "الله يوفقك ويرزقك مشوار طيب 🤲🚘",

    "على بركة الله يا كابتن، رافقتك السلامة 🌹",

    "الله يرزقك ويرزق العميل، مشوار موفق 🚕✨",

    "بيض الله وجهك يا كابتن، الله يوفقك 🤲",

    "تم تسجيل جاهزيتك، رزقك الله بالمشوار الطيب 🚘🌹",

    "الله يفتحها بوجهك ويرزقك من واسع فضله 🤲🚕",
]


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
]


LOCATION_END_PHRASES = [

    "لاي مشوار",
    "لاي مشاوير",
    "لأي مشوار",
    "لأي مشاوير",
    "للمشاوير",
    "لأي طلب",
    "متوفر للمشاوير",
    "متوفر لأي مشوار",
]


def is_location(text):

    normalized = normalize_arabic(
        text
    )

    has_location_phrase = any(

        normalize_arabic(phrase)
        in normalized

        for phrase in LOCATION_PHRASES
    )

    if has_location_phrase:
        return True

    if re.search(
        r"(?:متواجد|موجود|متوفر)\s+"
        r"(?:حاليا\s+)?(?:في|ب)\s+",
        normalized,
    ):

        return True

    return False


def looks_like_driver_location(text):

    normalized = normalize_arabic(
        text
    )

    if not is_location(text):
        return False

    for phrase in LOCATION_END_PHRASES:

        if (
            normalize_arabic(phrase)
            in normalized
        ):

            return True

    return True


async def handle_location(
    update,
    context,
):

    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    text = clean_text(
        message.text or ""
    )

    if not text:
        return False

    if not looks_like_driver_location(
        text
    ):
        return False

    driver_registered = is_driver(
        user.id
    )

    if not driver_registered:

        auto_driver_phrases = [

            "لاي مشوار",
            "لاي مشاوير",
            "لأي مشوار",
            "لأي مشاوير",
            "للمشاوير",
            "متوفر للمشاوير",
            "متوفر لأي مشوار",
        ]

        normalized = normalize_arabic(
            text
        )

        if any(

            normalize_arabic(p)
            in normalized

            for p in auto_driver_phrases
        ):

            mark_driver(user)

            driver_registered = True

    if not driver_registered:

        await message.reply_text(

            "📍 هذا الإعلان مخصص للكباتن فقط 🚕\n\n"

            "إذا أنت كابتن اضغط «🚕 أنا كابتن» مرة واحدة، "
            "وبعدها البوت بيتعرف عليك تلقائيًا."
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

    if already:

        await message.reply_text(

            "😂 عرفنا وينك اليوم.\n\n"

            "📍 إعلان التواجد مسموح مرة واحدة فقط باليوم."
        )

        return True

    await message.reply_text(

        f"📍 <b>تم تسجيل تواجد الكابتن</b>\n\n"

        f"{display_user(user)}\n\n"

        f"📌 {html(text)}\n\n"

        "🚕 تم تسجيل موقعك، الله يرزقك مشوار طيب.",

        parse_mode=ParseMode.HTML,
    )

    return True


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
    "ممكن توصيل",
    "ممكن مشوار",
    "فيه كابتن",
    "في كابتن",
    "احد رايح",
    "كابتن يوديني",
    "عندي مشوار",
    "مشوار من",
    "توصيل من",
    "ودي اروح من",
]


def looks_like_trip(text):

    if not text:
        return False

    normalized = normalize_arabic(
        text
    )

    if looks_like_driver_location(
        text
    ):
        return False

    for phrase in TRIP_PHRASES:

        if (
            normalize_arabic(phrase)
            in normalized
        ):

            return True

    if "→" in text or "->" in text:
        return True

    if re.search(
        r"\bمن\s+.+?\s+"
        r"(?:الى|الي|إلى|إلي)\s+.+",
        text,
        re.IGNORECASE,
    ):

        return True

    return False


def extract_route(text):

    original = clean_text(
        text
    )

    match = re.search(

        r"من\s+(.+?)\s+"
        r"(?:الى|إلى|إلي|الي)\s+(.+)",

        original,

        re.IGNORECASE,
    )

    if match:

        start = match.group(1).strip()

        destination = (
            match.group(2).strip()
        )

        return start, destination

    for separator in [
        "→",
        "->",
    ]:

        if separator not in original:
            continue

        parts = original.split(
            separator,
            1,
        )

        if len(parts) == 2:

            start = parts[0].strip()

            destination = (
                parts[1].strip()
            )

            if (
                len(start) >= 2
                and len(destination) >= 2
            ):

                start = re.sub(

                    r"^(ابغى|ابغا|ابي|احتاج|محتاج|مشوار|توصيل)\s+",

                    "",

                    start,

                    flags=re.IGNORECASE,
                )

                return (
                    start,
                    destination,
                )

    return None, None


# ============================================================
# تسجيل رسالة العميل الأصلية
# ============================================================

async def register_trip_message(
    message
):

    customer = message.from_user

    if not customer:
        return

    text = clean_text(
        message.text or ""
    )

    if not text:
        return

    start, destination = extract_route(
        text
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
            message.message_id,
            customer.id,
            customer.username or "",
            datetime.now(
                SAUDI_TZ
            ).isoformat(),
            start or "",
            destination or "",
            text,
        ))

        con.commit()


# ============================================================
# الحصول على المشوار
# ============================================================

def get_trip(trip_id):

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            SELECT
                message_id,
                customer_id,
                customer_username,
                created_at,
                start,
                destination,
                original_text
            FROM trips
            WHERE message_id = ?
        """, (trip_id,))

        return cur.fetchone()


# ============================================================
# 🚕 إنشاء كرت الكابتن
# ============================================================

async def create_ready_card(
    update,
    context,
    customer_id,
    driver,
    trip_id,
):

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
            return False

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

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📩 تواصل مع العميل",
                callback_data=(
                    f"contact_customer:"
                    f"{trip_id}:"
                    f"{driver.id}"
                ),
            ),

            InlineKeyboardButton(
                "🚕 تواصل مع الكابتن",
                callback_data=(
                    f"contact_driver:"
                    f"{trip_id}:"
                    f"{driver.id}"
                ),
            ),
        ]

    ])

    driver_name = html(
        driver.full_name
    )

    await context.bot.send_message(

        chat_id=GROUP_ID,

        text=(

            "🚕 <b>كابتن قريب منك</b>\n\n"

            f"👨‍✈️ <b>{driver_name}</b>\n\n"

            "تم تسجيل جاهزية الكابتن لهذا الطلب ✅\n"

            "💰 السعر والتفاهم بالخاص."
        ),

        parse_mode=ParseMode.HTML,

        reply_markup=keyboard,

        reply_to_message_id=trip_id,
    )

    return True


# ============================================================
# 🚕 READY
# ============================================================

async def handle_ready_reply(
    update,
    context,
):

    message = update.message
    driver = update.effective_user

    if not message or not driver:
        return False

    text = clean_text(
        message.text or ""
    )

    if not is_driver_ready(text):
        return False

    replied = (
        message.reply_to_message
    )

    if not replied:

        return False

    original_message = replied

    if original_message.from_user:

        if original_message.from_user.is_bot:

            await message.reply_text(

                "🚕 إذا تبي تأخذ مشوار، رد على "
                "<b>رسالة العميل الأصلية</b> "
                "واكتب «جاهز».",

                parse_mode=ParseMode.HTML,
            )

            return True

    trip_id = (
        original_message.message_id
    )

    trip = get_trip(
        trip_id
    )

    if not trip:

        original_text = (

            original_message.text
            or original_message.caption
            or ""
        )

        if not looks_like_trip(
            original_text
        ):

            await message.reply_text(

                "🚕 هذه ليست رسالة طلب مشوار مسجلة.\n\n"

                "رد على رسالة العميل التي فيها طلب المشوار "
                "واكتب «جاهز»."
            )

            return True

        customer = (
            original_message.from_user
        )

        if not customer:

            await message.reply_text(
                "⚠️ ما قدرت أحدد صاحب طلب المشوار."
            )

            return True

        save_user(customer)

        if not is_customer(
            customer.id
        ):

            mark_customer(
                customer
            )

        await register_trip_message(
            original_message
        )

        trip = get_trip(
            trip_id
        )

    if not trip:

        await message.reply_text(
            "⚠️ تعذر تسجيل هذا المشوار، حاول مرة ثانية."
        )

        return True

    customer_id = trip[1]

    save_user(driver)

    # ========================================================
    # أي شخص يضغط جاهز يتم تسجيله ككابتن
    # ========================================================

    mark_driver(driver)

    if driver.id == customer_id:

        await message.reply_text(

            "😂 يا عميل، ما ينفع تكون كابتن وعميل لنفس الطلب."
        )

        return True

    created = await create_ready_card(

        update,
        context,
        customer_id,
        driver,
        trip_id,
    )

    if not created:

        await message.reply_text(
            "✅ أنت مسجل جاهز لهذا المشوار بالفعل."
        )

        return True

    await message.reply_text(
        random.choice(READY_MESSAGES)
    )

    return True


# ============================================================
# 📩 تواصل مع العميل
# ============================================================

async def contact_customer_button(
    update,
    context,
):

    query = update.callback_query

    user = query.from_user

    if not query or not user:
        return

    try:

        parts = query.data.split(":")

        trip_id = int(parts[1])

        driver_id = int(parts[2])

    except Exception:

        await query.answer(
            "بيانات الزر غير صحيحة.",
            show_alert=True,
        )

        return

    if user.id != driver_id:

        await query.answer(

            "🚫 هذا الزر مخصص للكابتن الذي سجل جاهز لهذا المشوار.",

            show_alert=True,
        )

        return

    trip = get_trip(
        trip_id
    )

    if not trip:

        await query.answer(

            "⚠️ بيانات المشوار غير موجودة.",

            show_alert=True,
        )

        return

    customer_id = trip[1]

    customer_username = (
        trip[2] or ""
    )

    saved_username = get_username(
        customer_id
    )

    if saved_username:
        customer_username = saved_username

    if customer_username:

        username = (
            customer_username
            .lstrip("@")
        )

        await query.answer(

            "📩 فتح تواصل العميل...",

            url=(
                f"https://t.me/{username}"
            ),
        )

        return

    await query.answer(

        "📩 فتح تواصل العميل...",

        url=(
            f"tg://user?id={customer_id}"
        ),
    )


# ============================================================
# 🚕 تواصل مع الكابتن
# ============================================================

async def contact_driver_button(
    update,
    context,
):

    query = update.callback_query

    user = query.from_user

    if not query or not user:
        return

    try:

        parts = query.data.split(":")

        trip_id = int(parts[1])

        driver_id = int(parts[2])

    except Exception:

        await query.answer(
            "بيانات الزر غير صحيحة.",
            show_alert=True,
        )

        return

    trip = get_trip(
        trip_id
    )

    if not trip:

        await query.answer(

            "⚠️ بيانات المشوار غير موجودة.",

            show_alert=True,
        )

        return

    customer_id = trip[1]

    if user.id != customer_id:

        await query.answer(

            "🚫 هذا الزر مخصص لصاحب طلب المشوار فقط.",

            show_alert=True,
        )

        return

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            SELECT 1
            FROM ready
            WHERE trip_id = ?
            AND driver_id = ?
        """, (
            trip_id,
            driver_id,
        ))

        ready = cur.fetchone()

    if not ready:

        await query.answer(

            "⚠️ هذا الكابتن غير مسجل لهذا المشوار.",

            show_alert=True,
        )

        return

    username = get_username(
        driver_id
    )

    if username:

        username = (
            username
            .lstrip("@")
        )

        await query.answer(

            "🚕 فتح تواصل الكابتن...",

            url=(
                f"https://t.me/{username}"
            ),
        )

        return

    await query.answer(

        "🚕 فتح تواصل الكابتن...",

        url=(
            f"tg://user?id={driver_id}"
        ),
    )


# ============================================================
# ROLE BUTTONS
# ============================================================

async def role_selection_button(
    update,
    context,
):

    query = update.callback_query

    data = query.data or ""

    clicked_by = query.from_user

    if not clicked_by:

        await query.answer()

        return

    try:

        role, target_id = data.split(
            ":",
            1,
        )

        target_id = int(
            target_id
        )

    except Exception:

        await query.answer()

        return

    admin = await is_admin(
        update,
        context,
    )

    if (
        clicked_by.id != target_id
        and not admin
    ):

        await query.answer(

            "هذا الزر مخصص للعضو الجديد أو للمسؤول فقط 🙏",

            show_alert=True,
        )

        return

    if clicked_by.id == target_id:

        save_user(
            clicked_by
        )

    else:

        row = get_user_info(
            target_id
        )

        if not row:

            await query.answer(

                "لم يتم العثور على بيانات العضو.",

                show_alert=True,
            )

            return

    if role == "role_driver":

        mark_driver_by_id(
            target_id
        )

        await query.answer(

            "تم تسجيلك ككابتن 🚕 وسيتم التعرف عليك تلقائيًا.",

            show_alert=True,
        )

        target_display = display_saved_user(
            target_id
        )

        if clicked_by.id == target_id:

            text = (

                f"{target_display}\n\n"

                "✅ تم تسجيلك ككابتن بنجاح.\n\n"

                "من الآن البوت يعرف أنك كابتن، "
                "وما تحتاج تضغط الزر مرة ثانية.\n\n"

                "🚕 إذا شفت طلب مشوار يناسبك:\n"

                "رد على <b>رسالة العميل نفسها</b> واكتب:\n"

                "<b>جاهز</b>\n\n"

                "📍 وإذا كنت متواجد في حي معين، "
                "اكتب مثلًا:\n"

                "أنا موجود في الحمدانية لأي مشوار."
            )

        else:

            text = (

                "👑 <b>تم تعديل صفة العضو</b>\n\n"

                f"👤 العضو: {target_display}\n"

                f"🏷️ الصفة: <b>{html(DRIVER_BADGE)}</b>\n\n"

                "تم حفظ التعديل بنجاح ✅"
            )

        await query.message.reply_text(

            text,

            parse_mode=ParseMode.HTML,
        )

        return

    if role == "role_customer":

        mark_customer_by_id(
            target_id
        )

        await query.answer(

            "تم تسجيل العضو كعميل 🧑🏻‍💼",

            show_alert=True,
        )

        target_display = display_saved_user(
            target_id
        )

        if clicked_by.id == target_id:

            text = (

                f"{target_display}\n\n"

                "أهلاً فيك 🌹\n\n"

                "🧑🏻‍💼 <b>لطلب مشوار:</b>\n"

                "اكتب طلبك مباشرة في القروب.\n\n"

                "مثال:\n"

                "السلام عليكم، أبغى مشوار من الحمدانية إلى المطار.\n\n"

                "🚕 وإذا رد كابتن على طلبك وكتب «جاهز»، "
                "بيظهر كرت صغير للتواصل معه."
            )

        else:

            text = (

                "👑 <b>تم تعديل صفة العضو</b>\n\n"

                f"👤 العضو: {target_display}\n"

                f"🏷️ الصفة: <b>{html(CUSTOMER_BADGE)}</b>\n\n"

                "تم حفظ التعديل بنجاح ✅"
            )

        await query.message.reply_text(

            text,

            parse_mode=ParseMode.HTML,
        )


# ============================================================
# COMPLAINTS
# ============================================================

async def complaint_button(
    update,
    context,
):

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

    r"(https?://\S+"
    r"|www\.\S+"
    r"|t\.me/\S+"
    r"|telegram\.me/\S+)",

    re.IGNORECASE,
)


def _normalize_link(link):

    link = link.lower().rstrip("/")

    for prefix in (
        "https://",
        "http://",
    ):

        if link.startswith(prefix):

            link = link[
                len(prefix):
            ]

            break

    return link


# ============================================================
# الروابط المسموحة
# ============================================================

ALLOWED_LINK_NORMALIZED = (
    _normalize_link(
        ALLOWED_GROUP_LINK
    )
)


ALLOWED_GOOGLE_MAPS_DOMAINS = [

    "maps.google.com",

    "google.com/maps",

    "www.google.com/maps",

    "maps.app.goo.gl",

    "goo.gl/maps",
]


def is_google_maps_link(link):

    normalized = _normalize_link(
        link
    )

    for domain in ALLOWED_GOOGLE_MAPS_DOMAINS:

        if normalized.startswith(
            domain
        ):

            return True

    return False


def forbidden_link(text):

    if not text:
        return False

    for link in URL_PATTERN.findall(
        text
    ):

        link = link.rstrip(
            ".,!?؟،؛:)]}>\"'"
        )

        normalized = _normalize_link(
            link
        )

        # ====================================================
        # Google Maps مسموح
        # ====================================================

        if is_google_maps_link(
            link
        ):

            continue

        # ====================================================
        # رابط القروب الرسمي مسموح
        # ====================================================

        if normalized.startswith(
            ALLOWED_LINK_NORMALIZED
        ):

            continue

        # ====================================================
        # أي رابط آخر ممنوع
        # ====================================================

        return True

    return False


def is_forwarded(message):

    return bool(

        getattr(
            message,
            "forward_origin",
            None,
        )

        or getattr(
            message,
            "forward_from",
            None,
        )

        or getattr(
            message,
            "forward_from_chat",
            None,
        )

        or getattr(
            message,
            "forward_sender_name",
            None,
        )
    )


async def protect_message(
    update,
    context,
):

    message = update.message

    user = update.effective_user

    if not message or not user:
        return False

    if is_owner(user):
        return False

    if await is_admin(
        update,
        context,
    ):
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

            "الروابط ممنوعة في القروب 🚫\n\n"

            "📍 روابط Google Maps مسموحة."
        )

        return True

    return False


# ============================================================
# VIOLATIONS
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


def violation_reason(text):

    normalized = normalize_arabic(
        text
    )

    stripped = normalized.strip()

    if stripped in (
        "خاص",
        "الخاص",
    ):

        return "خاص"

    for word in BAD_WORDS:

        if (
            normalize_arabic(word)
            in normalized
        ):

            return "إساءة أو سب"

    for phrase in INAPPROPRIATE:

        if (
            normalize_arabic(phrase)
            in normalized
        ):

            return "كلام غير مناسب"

    # ========================================================
    # 💰 الأسعار مسموحة
    #
    # لا يوجد أي فحص يمنع:
    # 400
    # 400 - 450
    # 1200 ريال
    # 25 ريال
    # إلخ...
    # ========================================================

    return None


async def handle_violation(
    update,
    context,
    reason,
):

    message = update.message

    user = update.effective_user

    if not message or not user:
        return

    if is_owner(user):
        return

    if await is_admin(
        update,
        context,
    ):
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
                "رد على رسالة العميل واكتب «جاهز».\n\n"

                "📝 تم تسجيلها كمخالفة."
            ),

            parse_mode=ParseMode.HTML,
        )

        reason = "كتابة كلمة خاص"

    save_user(user)

    now = datetime.now(
        SAUDI_TZ
    )

    with db() as con:

        cur = con.cursor()

        cur.execute("""
            SELECT violations, last_violation_at
            FROM users
            WHERE user_id = ?
        """, (user.id,))

        row = cur.fetchone()

        current = (
            row[0]
            if row
            else 0
        )

        last_at = (
            row[1]
            if row
            else None
        )

        if last_at:

            try:

                last_dt = datetime.fromisoformat(
                    last_at
                )

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

    try:

        await message.delete()

    except Exception:
        pass

    if count >= 4:

        try:

            until = (

                datetime.now(
                    SAUDI_TZ
                )

                + timedelta(
                    hours=MUTE_HOURS
                )
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

                    "🔇 <b>تم كتم العضو</b>\n\n"

                    f"{display_user(user)}\n\n"

                    "🔴 المخالفة رقم "
                    f"<b>{count}</b>\n"

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
# CHAT
# ============================================================

async def handle_chat_response(
    message
):

    text = message.text or ""

    response = get_greeting(
        text
    )

    if not response:
        return False

    if looks_like_trip(text):
        return False

    if looks_like_driver_location(
        text
    ):
        return False

    if is_driver_ready(text):
        return False

    await message.reply_text(
        response
    )

    return True


# ============================================================
# MESSAGE HANDLER
# ============================================================

async def message_handler(
    update,
    context,
):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    save_user(user)

    # ========================================================
    # حماية الرسائل
    # ========================================================

    if await protect_message(
        update,
        context,
    ):

        return

    text = message.text or ""

    if not text:
        return

    # ========================================================
    # المخالفات
    # ========================================================

    reason = violation_reason(
        text
    )

    if reason:

        if is_driver_ready(text):

            handled = await handle_ready_reply(
                update,
                context,
            )

            if handled:
                return

        await handle_violation(

            update,
            context,
            reason,
        )

        return

    # ========================================================
    # 🚕 جاهز
    # ========================================================

    if is_driver_ready(text):

        handled = await handle_ready_reply(
            update,
            context,
        )

        if handled:
            return

        if not message.reply_to_message:

            if is_driver(user.id):

                await message.reply_text(

                    "🚕 يا كابتن، عشان أسجل جاهزيتك لمشوار معين:\n\n"

                    "↩️ رد على <b>رسالة العميل نفسها</b> "
                    "واكتب «جاهز».\n\n"

                    "كذا أعرف أي مشوار تقصد بالضبط.",

                    parse_mode=ParseMode.HTML,
                )

                return

            await message.reply_text(

                "🚕 إذا أنت كابتن، اضغط «أنا كابتن» أولًا، "
                "ثم رد على رسالة العميل نفسها واكتب «جاهز»."
            )

            return

    # ========================================================
    # 📍 موقع الكابتن
    # ========================================================

    if looks_like_driver_location(
        text
    ):

        await handle_location(
            update,
            context,
        )

        return

    # ========================================================
    # طلب مشوار
    #
    # الرسالة الأصلية تبقى كما هي.
    # لا بطاقة بديلة.
    # السعر مسموح.
    # Google Maps مسموح.
    # ========================================================

    if looks_like_trip(text):

        mark_customer(user)

        await register_trip_message(
            message
        )

        return

    # ========================================================
    # الردود العادية
    # ========================================================

    if await handle_chat_response(
        message
    ):

        return


# ============================================================
# التذكير
# ============================================================

async def interactive_reminder(
    context,
):

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

async def callback_handler(
    update,
    context,
):

    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    # ========================================================
    # القوانين
    # ========================================================

    if data == "rules":

        await query.answer()

        await query.message.reply_text(
            RULES
        )

        return

    # ========================================================
    # تواصل مع العميل
    # ========================================================

    if data.startswith(
        "contact_customer:"
    ):

        await contact_customer_button(
            update,
            context,
        )

        return

    # ========================================================
    # تواصل مع الكابتن
    # ========================================================

    if data.startswith(
        "contact_driver:"
    ):

        await contact_driver_button(
            update,
            context,
        )

        return

    # ========================================================
    # تسجيل عميل / كابتن
    # ========================================================

    if (
        data.startswith(
            "role_customer:"
        )
        or data.startswith(
            "role_driver:"
        )
    ):

        await role_selection_button(
            update,
            context,
        )

        return

    # ========================================================
    # الشكاوى
    # ========================================================

    if data.startswith(
        "complaint:"
    ):

        await complaint_button(
            update,
            context,
        )

        return

    await query.answer()


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

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
        "🚘 Starting Mishawir Jeddah Bot...",
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

    # ========================================================
    # التذكير كل 30 دقيقة
    # ========================================================

    application.job_queue.run_repeating(

        interactive_reminder,

        interval=REMINDER_INTERVAL,

        first=REMINDER_INTERVAL,

        name="interactive_group_reminder",
    )

    # ========================================================
    # COMMANDS
    # ========================================================

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

    # ========================================================
    # NEW MEMBERS
    # ========================================================

    application.add_handler(

        MessageHandler(

            filters.StatusUpdate.NEW_CHAT_MEMBERS,

            welcome,
        )
    )

    # ========================================================
    # LEFT MEMBERS
    # ========================================================

    application.add_handler(

        MessageHandler(

            filters.StatusUpdate.LEFT_CHAT_MEMBER,

            member_left_handler,
        )
    )

    # ========================================================
    # BUTTONS
    # ========================================================

    application.add_handler(

        CallbackQueryHandler(
            callback_handler
        )
    )

    # ========================================================
    # TEXT
    # ========================================================

    application.add_handler(

        MessageHandler(

            filters.TEXT & ~filters.COMMAND,

            message_handler,
        )
    )

    # ========================================================
    # ERRORS
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    print(
        "✅ Bot is running...",
        flush=True,
    )

    print(
        "📢 Interactive reminders: every 30 minutes",
        flush=True,
    )

    print(
        "🚕 Trip system: original customer messages",
        flush=True,
    )

    print(
        "💰 Prices are allowed",
        flush=True,
    )

    print(
        "📍 Google Maps links are allowed",
        flush=True,
    )

    print(
        "↩️ Drivers must reply to customer message with READY",
        flush=True,
    )

    print(
        "👋 Member leave monitoring: OWNER private notification",
        flush=True,
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
