import os
import re
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

GROUP_NAME = "🚘 مشاوير جدة • مكة • الطائف • جميع المناطق"

OWNER_USERNAME = "klodi500"
ADMIN_USERNAME = "klodi500"

ALLOWED_GROUP_LINK = "https://t.me/JeddahRides"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

IDLE_MINUTES = 30


# ============================================================
# CHECK TOKEN
# ============================================================

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود. تأكد من إضافته في GitHub Secrets باسم BOT_TOKEN."
    )


# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            is_driver INTEGER DEFAULT 0,
            violations INTEGER DEFAULT 0
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
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        INSERT OR IGNORE INTO settings(key, value)
        VALUES ('idle_enabled', '1')
    """)

    con.commit()
    con.close()


def get_setting(key, default=None):
    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key = ?",
        (key,)
    )

    row = cur.fetchone()

    con.close()

    return row[0] if row else default


def set_setting(key, value):
    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value
    """, (key, str(value)))

    con.commit()
    con.close()


# ============================================================
# USERS
# ============================================================

def save_user(user):
    if not user:
        return

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT INTO users(user_id, name, username)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            name = excluded.name,
            username = excluded.username
    """, (
        user.id,
        user.full_name,
        user.username or ""
    ))

    con.commit()
    con.close()


def mark_driver(user):
    if not user:
        return

    save_user(user)

    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET is_driver = 1
        WHERE user_id = ?
    """, (user.id,))

    con.commit()
    con.close()


def is_driver(user_id):
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT is_driver
        FROM users
        WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()

    con.close()

    return bool(row and row[0] == 1)


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

    if user.username:
        return (
            f'<a href="https://t.me/{user.username}">'
            f"<b>{name}</b>"
            f"</a>"
        )

    return f"<b>{name}</b>"


def is_owner(user):
    if not user or not user.username:
        return False

    return user.username.lower() == OWNER_USERNAME.lower()


async def is_admin(update, context):
    user = update.effective_user

    if not user:
        return False

    if is_owner(user):
        return True

    try:
        member = await context.bot.get_chat_member(
            GROUP_ID,
            user.id
        )

        return member.status in (
            "administrator",
            "creator"
        )

    except Exception:
        return False


# ============================================================
# RULES
# ============================================================

DEFAULT_RULES = f"""
📋 قوانين {GROUP_NAME}

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه بطريقته الطبيعية.

3️⃣ الكابتن الجاهز يضغط «جاهز للمشوار».

4️⃣ 🚫 يمنع كتابة «خاص» داخل القروب.

5️⃣ 💰 السعر والتفاهم بالخاص.

6️⃣ 🤝 الاحترام واجب على الجميع.

7️⃣ 🚫 يمنع السب والإساءة.

8️⃣ 📍 إعلان التواجد للكباتن مرة واحدة باليوم.

9️⃣ 🔄 الرسائل المحولة ممنوعة.

🔟 🔗 الروابط ممنوعة باستثناء رابط القروب الرسمي.

⚠️ نظام المخالفات:

الأولى → تحذير.
الثانية → تحذير.
الثالثة → كتم 24 ساعة.
الرابعة → حظر.

📩 الإدارة:
@{ADMIN_USERNAME}
"""


def get_rules():
    custom = get_setting("rules_text", "")

    if custom and custom.strip():
        return custom

    return DEFAULT_RULES


async def rules(update, context):
    if not update.message:
        return

    await update.message.reply_text(
        get_rules()
    )


# ============================================================
# WELCOME
# ============================================================

async def welcome(update, context):
    message = update.message

    if not message:
        return

    members = message.new_chat_members or []

    for member in members:
        if member.is_bot:
            continue

        save_user(member)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📋 القوانين",
                    callback_data="rules"
                )
            ],
            [
                InlineKeyboardButton(
                    "📩 الإدارة",
                    url=f"https://t.me/{ADMIN_USERNAME}"
                )
            ]
        ])

        await message.reply_text(
            f"👋 يا هلا {display_user(member)} 🌹\n\n"
            f"نورت {GROUP_NAME} 🚗\n\n"
            "🚗 عندك مشوار؟\n"
            "اكتب طلبك مباشرة.\n\n"
            "👨‍✈️ كابتن؟\n"
            "اكتب «كابتن وجاهز».\n\n"
            "📋 اضغط القوانين لمعرفة نظام القروب.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )


# ============================================================
# TRIPS
# ============================================================

TRIP_PHRASES = [
    "ابغى مشوار",
    "ابي مشوار",
    "ابغا مشوار",
    "ابغى توصيل",
    "ابي توصيل",
    "ابغا توصيل",
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
    "ابي اروح",
    "ودي اروح",
    "ممكن توصيل",
    "ممكن مشوار",
    "فيه كابتن",
    "في كابتن",
    "احد رايح",
    "كابتن من",
    "كابتن يوديني",
    "عندي مشوار",
    "مشوار من",
    "توصيل من",
]


def looks_like_trip(text):
    normalized = normalize_arabic(text)

    for phrase in TRIP_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    if re.search(
        r"\bمن\b.+\b(?:الى|الي)\b",
        normalized
    ):
        return True

    if "→" in text or "->" in text:
        return True

    return False


def extract_route(text):
    original = clean_text(text)
    normalized = normalize_arabic(original)

    match = re.search(
        r"من\s+(.+?)\s+(?:الى|الي)\s+(.+)",
        normalized
    )

    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip()
        )

    for separator in [
        "→",
        "->",
        " - ",
    ]:
        if separator in original:
            parts = original.split(
                separator,
                1
            )

            if len(parts) == 2:
                start = parts[0].strip()
                destination = parts[1].strip()

                if (
                    len(start) >= 2
                    and len(destination) >= 2
                ):
                    return (
                        start,
                        destination
                    )

    return None, None


async def create_trip(message, context):
    customer = message.from_user

    if not customer:
        return

    original_text = clean_text(
        message.text or ""
    )

    start, destination = extract_route(
        original_text
    )

    if start and destination:
        route = (
            f"📍 <b>من:</b> {html(start)}\n"
            f"🏁 <b>إلى:</b> {html(destination)}"
        )
    else:
        route = (
            "📍 <b>تفاصيل المشوار:</b>\n"
            f"{html(original_text)}"
        )

    sent = await message.reply_text(
        "🚗 <b>طلب مشوار جديد</b>\n\n"
        f"👤 <b>العميل:</b> "
        f"{display_user(customer)}\n\n"
        f"{route}\n\n"
        "👨‍✈️ الكابتن الجاهز يضغط الزر.\n"
        "💰 التفاهم والسعر بالخاص.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "👨‍✈️ جاهز للمشوار",
                    callback_data="ready:0"
                )
            ]
        ])
    )

    con = db()
    cur = con.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO trips(
            message_id,
            customer_id,
            created_at,
            start,
            destination,
            original_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        sent.message_id,
        customer.id,
        datetime.now(
            SAUDI_TZ
        ).isoformat(),
        start or "",
        destination or "",
        original_text
    ))

    con.commit()
    con.close()

    await sent.edit_reply_markup(
        InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "👨‍✈️ جاهز للمشوار",
                    callback_data=(
                        f"ready:{sent.message_id}"
                    )
                )
            ]
        ])
    )


# ============================================================
# DRIVER
# ============================================================

DRIVER_READY_PHRASES = [
    "كابتن وجاهز",
    "كابتن جاهز",
    "انا كابتن",
    "جاهز لاي مشوار",
    "جاهز للمشاوير",
    "متوفر للمشاوير",
    "متوفر لاي مشوار",
    "كابتن ومتواجد",
    "كابتن متواجد",
]


def is_driver_ready_message(text):
    normalized = normalize_arabic(text)

    return any(
        normalize_arabic(phrase)
        in normalized
        for phrase in DRIVER_READY_PHRASES
    )


async def handle_driver_ready(message):
    user = message.from_user

    if not user:
        return False

    if not is_driver_ready_message(
        message.text or ""
    ):
        return False

    mark_driver(user)

    await message.reply_text(
        f"👨‍✈️ {display_user(user)}\n\n"
        "✅ تم تسجيلك ككابتن.\n"
        "🚗 أنت الآن مسجل ضمن الكباتن.",
        parse_mode=ParseMode.HTML
    )

    return True


# ============================================================
# READY BUTTON
# ============================================================

async def ready_button(update, context):
    query = update.callback_query

    await query.answer()

    try:
        trip_id = int(
            query.data.split(":")[1]
        )
    except Exception:
        return

    driver = query.from_user

    mark_driver(driver)

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT customer_id, start, destination
        FROM trips
        WHERE message_id = ?
    """, (trip_id,))

    trip = cur.fetchone()

    if not trip:
        con.close()

        await query.answer(
            "الطلب غير موجود.",
            show_alert=True
        )

        return

    start = trip[1]
    destination = trip[2]

    cur.execute("""
        SELECT 1
        FROM ready
        WHERE trip_id = ?
        AND driver_id = ?
    """, (
        trip_id,
        driver.id
    ))

    if cur.fetchone():
        con.close()

        await query.answer(
            "أنت مسجل لهذا المشوار بالفعل 😂",
            show_alert=True
        )

        return

    cur.execute("""
        INSERT INTO ready(
            trip_id,
            driver_id
        )
        VALUES (?, ?)
    """, (
        trip_id,
        driver.id
    ))

    con.commit()
    con.close()

    keyboard = None

    if driver.username:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📩 تواصل مع الكابتن",
                    url=(
                        f"https://t.me/"
                        f"{driver.username}"
                    )
                )
            ]
        ])

    route = ""

    if start and destination:
        route = (
            f"\n📍 {html(start)} → "
            f"{html(destination)}"
        )

    await context.bot.send
