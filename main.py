import os
import random
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


# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_ID = -1003716441020

GROUP_NAME = "🚘 مشاوير جدة • مكة • الطائف • جميع المناطق"

OWNER_USERNAME = "klodi500"
ADMIN_USERNAME = "klodi500"

ALLOWED_GROUP_LINK = "https://t.me/JeddahRides"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

IDLE_MINUTES = 30


# =========================
# GLOBAL STATE
# =========================

last_activity = datetime.now(SAUDI_TZ)
last_idle_message = None
idle_turn = 0

conversation_state = {}


# =========================
# IDLE MESSAGES
# =========================

CUSTOMER_IDLE_MESSAGES = [
    "🚗 عندك مشوار؟\n\nاكتب من وين إلى وين، والكباتن يشوفون طلبك 👨‍✈️",
    "📍 محتاج توصيل؟\n\nاكتب موقع الانطلاق والوجهة، ويمكن كابتنك يكون موجود الآن 🚘",
    "🚗 يا أهل المشاوير\n\nاللي عنده مشوار يكتب طلبه بطريقته الطبيعية 👌",
    "📢 محتاج مشوار اليوم؟\n\nجدة • مكة • الطائف • وجميع المناطق 🚗",
]

DRIVER_IDLE_MESSAGES = [
    "👨‍✈️ يا كباتن\n\nخلك قريب 🚗 يمكن ينزل الآن طلب يناسب خطك.",
    "🚘 يا أهل القيادة\n\nفيه عملاء ممكن يحتاجون مشاوير الآن، خلكم جاهزين 👨‍✈️",
    "👨‍✈️ الكابتن الجاهز يكسب الوقت.\n\nتابع الطلبات الجديدة 🚗",
    "🚗 رزقك يمكن يكون بالطلب الجاي.\n\nخلك متابع يا كابتن 👨‍✈️",
]

GENERAL_IDLE_MESSAGES = [
    "🚗 القروب هادي شوي 😂\n\nاللي عنده مشوار يكتب من وين إلى وين.",
    "👀 وين أهل المشاوير؟\n\nعميل يحتاج توصيل؟ كابتن ينتظر طلب؟ 🚘",
    "📍 مشوار جدة، مكة، الطائف أو أي منطقة؟\n\nاكتب طلبك 🚗",
    "🤲 الله يرزق الجميع.\n\nعميل يحتاج مشوار؟ كابتن ينتظر رزقه؟ 🚘",
]


# =========================
# DATABASE
# =========================

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


# =========================
# USERS
# =========================

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


# =========================
# OWNER / ADMIN
# =========================

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

        return member.status in ("administrator", "creator")

    except Exception:
        return False


# =========================
# HTML
# =========================

def html(text):
    if not text:
        return ""

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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


# =========================
# TEXT
# =========================

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


# =========================
# TRIPS
# =========================

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
    text = normalize_arabic(text)

    for phrase in TRIP_PHRASES:
        if normalize_arabic(phrase) in text:
            return True

    if re.search(r"\bمن\b.+\b(?:الى|الي)\b", text):
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

    for separator in ["→", "->", " - "]:
        if separator in original:
            parts = original.split(separator, 1)

            if len(parts) == 2:
                start = parts[0].strip()
                destination = parts[1].strip()

                if len(start) >= 2 and len(destination) >= 2:
                    return start, destination

    return None, None


async def create_trip(message, context):
    customer = message.from_user

    original_text = clean_text(message.text or "")

    start, destination = extract_route(original_text)

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
        f"👤 <b>العميل:</b> {display_user(customer)}\n\n"
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
        datetime.now(SAUDI_TZ).isoformat(),
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
                    callback_data=f"ready:{sent.message_id}"
                )
            ]
        ])
    )


# =========================
# DRIVER
# =========================

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
        normalize_arabic(phrase) in normalized
        for phrase in DRIVER_READY_PHRASES
    )


async def handle_driver_ready(message):
    user = message.from_user

    if not user:
        return False

    if not is_driver_ready_message(message.text or ""):
        return False

    mark_driver(user)

    await message.reply_text(
        f"👨‍✈️ {display_user(user)}\n\n"
        "✅ تم تسجيلك ككابتن.\n"
        "🚗 أنت الآن مسجل ضمن الكباتن.",
        parse_mode=ParseMode.HTML
    )

    return True


# =========================
# READY BUTTON
# =========================

async def ready_button(update, context):
    query = update.callback_query
    await query.answer()

    try:
        trip_id = int(query.data.split(":")[1])
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
    """, (trip_id, driver.id))

    if cur.fetchone():
        con.close()

        await query.answer(
            "أنت مسجل لهذا المشوار بالفعل 😂",
            show_alert=True
        )
        return

    cur.execute("""
        INSERT INTO ready(trip_id, driver_id)
        VALUES (?, ?)
    """, (trip_id, driver.id))

    con.commit()
    con.close()

    keyboard = None

    if driver.username:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📩 تواصل مع الكابتن",
                    url=f"https://t.me/{driver.username}"
                )
            ]
        ])

    route = ""

    if start and destination:
        route = (
            f"\n📍 {html(start)} → "
            f"{html(destination)}"
        )

    await context.bot.send_message(
        GROUP_ID,
        f"👨‍✈️ <b>كابتن جاهز للمشوار</b>\n\n"
        f"👤 {display_user(driver)}"
        f"{route}\n\n"
        "💰 التفاهم والسعر بالخاص.",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        reply_to_message_id=trip_id
    )


# =========================
# RULES
# =========================

DEFAULT_RULES = f"""
📋 قوانين {GROUP_NAME}

1️⃣ القروب للمشاوير والنقل.

2️⃣ العميل يكتب طلبه بطريقته الطبيعية.

3️⃣ الكابتن الجاهز يضغط «جاهز للمشوار».

4️⃣ 🚫 يمنع كتابة «خاص».

5️⃣ 💰 السعر والتفاهم بالخاص.

6️⃣ 🤝 الاحترام واجب.

7️⃣ 🚫 يمنع السب والإساءة.

8️⃣ 📍 إعلان التواجد مرة واحدة باليوم.

9️⃣ 🔄 الرسائل المحولة ممنوعة.

🔟 🔗 الروابط ممنوعة باستثناء رابط القروب الرسمي.

⚠️ المخالفات:
الأولى → تحذير.
الثانية → تحذير.
الثالثة → كتم 24 ساعة.
الرابعة → حظر.

📩 الإدارة:
@{ADMIN_USERNAME}
"""


def get_rules():
    custom = get_setting("rules_text", "")
    return custom if custom.strip() else DEFAULT_RULES


async def rules(update, context):
    await update.message.reply_text(get_rules())


# =========================
# WELCOME
# =========================

async def welcome(update, context):
    message = update.message

    if not message:
        return

    for member in message.new_chat_members:
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


# =========================
# VIOLATIONS
# =========================

BAD_WORDS = [
    "يا غبي",
    "يا حمار",
    "يا كلب",
    "يا تافه",
    "قليل الادب",
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

    if normalized.strip() in ("خاص", "الخاص"):
        return "كتابة كلمة «خاص»"

    for word in BAD_WORDS:
        if normalize_arabic(word) in normalized:
            return "إساءة أو سب"

    for phrase in INAPPROPRIATE:
        if normalize_arabic(phrase) in normalized:
            return "كلام غير مناسب"

    return None


async def violation(update, context, reason):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return

    if is_owner(user):
        return

    if await is_admin(update, context):
        return

    save_user(user)

    con = db()
    cur = con.cursor()

    cur.execute("""
        UPDATE users
        SET violations = violations + 1
        WHERE user_id = ?
    """, (user.id,))

    cur.execute("""
        SELECT violations
        FROM users
        WHERE user_id = ?
    """, (user.id,))

    count = cur.fetchone()[0]

    con.commit()
    con.close()

    try:
        await message.delete()
    except Exception:
        pass

    if count >= 4:
        try:
            await context.bot.ban_chat_member(
                GROUP_ID,
                user.id
            )

            await context.bot.send_message(
                GROUP_ID,
                f"🚫 تم حظر {display_user(user)}\n\n"
                "بسبب تكرار المخالفات.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

        return

    if count == 3:
        try:
            until = datetime.now(SAUDI_TZ) + timedelta(hours=24)

            await context.bot.restrict_chat_member(
                GROUP_ID,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=False
                ),
                until_date=until
            )

            await context.bot.send_message(
                GROUP_ID,
                f"🔇 تم كتم {display_user(user)} لمدة 24 ساعة.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

        return

    await context.bot.send_message(
        GROUP_ID,
        f"⚠️ تنبيه {display_user(user)}\n\n"
        f"السبب: {html(reason)}\n"
        f"المخالفات: {count}/3",
        parse_mode=ParseMode.HTML
    )


# =========================
# LINKS / FORWARDS
# =========================

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
    re.IGNORECASE
)


def forbidden_link(text):
    if not text:
        return False

    for link in URL_PATTERN.findall(text):
        link = link.rstrip(".,!?؟،؛:)]}>\"'")

        if link.startswith(ALLOWED_GROUP_LINK):
            continue

        return True

    return False


def forwarded(message):
    return bool(
        getattr(message, "forward_origin", None)
        or getattr(message, "forward_from", None)
        or getattr(message, "forward_from_chat", None)
        or getattr(message, "forward_sender_name", None)
    )


async def protect_content(update, context):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    if is_owner(user):
        return False

    if await is_admin(update, context):
        return False

    if forwarded(message):
        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {display_user(user)}\n\n"
            "الرسائل المحولة ممنوعة 🚫\n"
            "اكتب الرسالة مباشرة.",
            parse_mode=ParseMode.HTML
        )

        return True

    text = message.text or message.caption or ""

    if forbidden_link(text):
        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {display_user(user)}\n\n"
            "الروابط ممنوعة في القروب 🚫\n"
            "باستثناء رابط القروب الرسمي.",
            parse_mode=ParseMode.HTML
        )

        return True

    return False


# =========================
# DRIVER LOCATION
# =========================

LOCATION_PHRASES = [
    "متواجد في",
    "متواجد ب",
    "موجود في",
    "موجود ب",
    "انا في",
    "انا متواجد في",
    "متواجد حاليا في",
    "موجود حاليا في",
]


def is_location(text):
    normalized = normalize_arabic(text)

    return any(
        normalize_arabic(phrase) in normalized
        for phrase in LOCATION_PHRASES
    )


async def handle_location(update, context):
    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    text = message.text or ""

    if not is_location(text):
        return False

    if not is_driver(user.id):
        await message.reply_text(
            "📍 هذا الإعلان مخصص للكباتن فقط 👨‍✈️\n\n"
            "إذا أنت كابتن، اكتب «كابتن وجاهز» أولًا."
        )
        return True

    today = datetime.now(SAUDI_TZ).date().isoformat()

    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT last_date
        FROM locations
        WHERE user_id = ?
    """, (user.id,))

    row = cur.fetchone()

    if row and row[0] == today:
        con.close()

        await message.reply_text(
            "😂 عرفنا وينك اليوم.\n\n"
            "📍 إعلان التواجد مسموح مرة واحدة فقط باليوم."
        )

        return True

    cur.execute("""
        INSERT OR REPLACE INTO locations(user_id, last_date)
        VALUES (?, ?)
    """, (user.id, today))

    con.commit()
    con.close()

    await message.reply_text(
        f"📍 تم تسجيل تواجد {display_user(user)}\n\n"
        f"📌 {html(text)}",
        parse_mode=ParseMode.HTML
    )

    return True


# =========================
# SIMPLE CHAT
# =========================

RESPONSES = {
    "how_are_you": [
        "بخير دامك بخير 😎🚗",
        "تمام
