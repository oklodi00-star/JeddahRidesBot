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

ALLOWED_GROUP_LINK = "https://t.me/JeddahRides"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

MUTE_HOURS = 24
VIOLATION_RESET_DAYS = 30
ADMIN_CACHE_SECONDS = 300

REMINDER_INTERVAL = 30 * 60

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

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_arabic(text):
    text = clean_text(text).lower()

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
        text = text.replace(old, new)

    return text


def display_user(user):
    if not user:
        return "عضو"

    name = html(user.full_name)

    # الاسم عادي وليس رابطًا
    return f"<b>{name}</b>"


def display_saved_user(user_id):
    row = get_user_info(user_id)

    if not row:
        return "العضو"

    _, name, _ = row

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
        "اكتب مثلًا:\n"
        "السلام عليكم، ابغى مشوار من الحمدانية إلى المطار.\n\n"
        "🚕 الكابتن:\n"
        "إذا يناسبك الطلب اضغط «جاهز للمشوار».\n\n"
        "📍 الكابتن يقدر يعلن موقعه مرة واحدة يوميًا."
    )


# ============================================================
# SMART GREETINGS
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
    normalized = normalize_arabic(text)

    for phrases, responses in GREETINGS:
        for phrase in phrases:

            p = normalize_arabic(phrase)

            if normalized.startswith(p):
                return random.choice(responses)

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
    normalized = normalize_arabic(text)

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

# عبارات تؤكد أن الكلام إعلان تواجد وليس طلب مشوار
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
    normalized = normalize_arabic(text)

    # إذا احتوت الرسالة على عبارة تواجد واضحة
    has_location_phrase = any(
        normalize_arabic(phrase) in normalized
        for phrase in LOCATION_PHRASES
    )

    if has_location_phrase:
        return True

    # صيغ إضافية مثل:
    # الحمدانية متواجد
    # الحمدانية موجود
    if re.search(
        r"(?:متواجد|موجود|متوفر)\s+(?:حاليا\s+)?(?:في|ب)\s+",
        normalized,
    ):
        return True

    return False


def looks_like_driver_location(text):
    normalized = normalize_arabic(text)

    if not is_location(text):
        return False

    # أي رسالة تواجد تحتوي على عبارات مثل "لأي مشوار"
    # تعتبر تواجد كابتن بشكل مؤكد
    for phrase in LOCATION_END_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    return True


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
    # مهم جدًا:
    # إذا كان العضو مسجل ككابتن، نعتمد على التسجيل المحفوظ.
    # لا نطلب منه الضغط على "أنا كابتن" مرة أخرى.
    # ========================================================

    driver_registered = is_driver(user.id)

    if not driver_registered:

        # إذا كانت الرسالة نفسها واضحة جدًا أنها تواجد كابتن،
        # نسجله ككابتن تلقائيًا بدل إزعاجه.
        auto_driver_phrases = [
            "لاي مشوار",
            "لاي مشاوير",
            "لأي مشوار",
            "لأي مشاوير",
            "للمشاوير",
            "متوفر للمشاوير",
            "متوفر لأي مشوار",
        ]

        normalized = normalize_arabic(text)

        if any(
            normalize_arabic(p) in normalized
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

    normalized = normalize_arabic(text)

    # ========================================================
    # حماية مهمة:
    # رسالة تواجد الكابتن ليست مشوارًا
    # ========================================================

    if looks_like_driver_location(text):
        return False

    for phrase in TRIP_PHRASES:

        if normalize_arabic(phrase) in normalized:
            return True

    if "→" in text or "->" in text:
        return True

    if re.search(
        r"\bمن\s+.+?\s+(?:الى|الي|إلى|إلي)\s+.+",
        text,
        re.IGNORECASE,
    ):
        return True

    return False


def extract_route(text):

    original = clean_text(text)

    match = re.search(
        r"من\s+(.+?)\s+(?:الى|إلى|إلي|الي)\s+(.+)",
        original,
        re.IGNORECASE,
    )

    if match:

        start = match.group(1).strip()
        destination = match.group(2).strip()

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
            destination = parts[1].strip()

            if len(start) >= 2 and len(destination) >= 2:

                start = re.sub(
                    r"^(ابغى|ابغا|ابي|احتاج|محتاج|مشوار|توصيل)\s+",
                    "",
                    start,
                    flags=re.IGNORECASE,
                )

                return start, destination

    return None, None


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

    # أي شخص يضغط جاهز يتم تسجيله ككابتن
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

        _, trip_id, driver_id = (
            query.data.split(":")
        )

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

        _, customer_id, driver_id = (
            query.data.split(":")
        )

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

    # ========================================================
    # مهم:
    # عند اختيار العضو لنفسه، نحفظ بياناته أولًا.
    # ========================================================

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

        # الحفظ الدائم للكابتن
        mark_driver_by_id(target_id)

        await query.answer(
            "تم تسجيلك ككابتن 🚕 وسيتم التعرف عليك تلقائيًا.",
            show_alert=True,
        )

        target_display = display_saved_user(
            target_id
        )

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

        target_display = display_saved_user(
            target_id
        )

        if clicked_by.id == target_id:

            text = (
                f"🧑🏻‍💼 {target_display}\n\n"
                "أهلاً فيك 🌹\n\n"
                "لطلب مشوار اكتب مثلًا:\n"
                "السلام عليكم، ابغى مشوار من الحمدانية إلى المطار 🚘"
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

    normalized = normalize_arabic(text)
    stripped = normalized.strip()

    if stripped in (
        "خاص",
        "الخاص",
    ):
        return "خاص"

    for word in BAD_WORDS:

        if normalize_arabic(word) in normalized:
            return "إساءة أو سب"

    for phrase in INAPPROPRIATE:

        if normalize_arabic(phrase) in normalized:
            return "كلام غير مناسب"

    if re.search(
        r"(?:السعر|بكم|كم|ريال|الاجره|الاجرة|تكلفه|التكلفة|المبلغ)\s*\d+",
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
                "اكتب «جاهز» أو اضغط زر جاهز على بطاقة المشوار.\n\n"
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
# MESSAGE HANDLER
# ============================================================

async def message_handler(update, context):

    message = update.message

    if not message:
        return

    user = update.effective_user

    if not user:
        return

    save_user(user)

    if await protect_message(update, context):
        return

    text = message.text or ""

    if not text:
        return

    reason = violation_reason(text)

    if reason:

        await handle_violation(
            update,
            context,
            reason,
        )

        return

    # ========================================================
    # التعديل المهم رقم 1:
    # نفحص تواجد الكابتن قبل المشوار.
    # ========================================================

    if looks_like_driver_location(text):

        await handle_location(
            update,
            context,
        )

        return

    # ========================================================
    # التعديل المهم رقم 2:
    # الجاهز يُعالج قبل المشوار.
    # ========================================================

    if is_driver_ready(text):

        # إذا كتب الكابتن "أنا كابتن" أو "جاهز"
        # يتم حفظه دائمًا ككابتن.
        mark_driver(user)

        await message.reply_text(
            f"🚕 {display_user(user)}\n\n"
            "تم تسجيلك ككابتن جاهز ✅\n"
            "ومن الآن البوت يعرف أنك كابتن.\n\n"
            "إذا تقصد مشوارًا معينًا، استخدم زر "
            "«جاهز للمشوار» الموجود على بطاقة المشوار.\n\n"
            "الله يرزقك ويرافقك السلامة 🌹",
            parse_mode=ParseMode.HTML,
        )

        return

    # ========================================================
    # بعد ذلك فقط نفحص هل الرسالة طلب مشوار.
    # ========================================================

    if looks_like_trip(text):

        mark_customer(user)

        await create_trip(
            message,
            context,
        )

        return

    if await handle_chat_response(message):
        return


# ============================================================
# التذكير
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
        "✅ Bot is running...",
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
