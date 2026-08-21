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

last_activity = datetime.now(SAUDI_TZ)
last_idle_message = None
idle_turn = 0


# =========================
# IDLE MESSAGES
# =========================

CUSTOMER_IDLE_MESSAGES = [
    "🚗 عندك مشوار؟\n\nاكتب من وين إلى وين، والكباتن يشوفون طلبك 👨‍✈️",
    "📍 محتاج توصيل؟\n\nاكتب موقع الانطلاق والوجهة، ويمكن كابتنك يكون موجود الآن 🚘",
    "🚗 يا أهل المشاوير\n\nاللي عنده مشوار يكتب طلبه بطريقته الطبيعية، والبوت يرتبه لكم 👌",
    "📢 محتاج مشوار اليوم؟\n\nجدة • مكة • الطائف • وجميع المناطق 🚗",
    "👀 يمكن فيه كابتن قريب منك الآن.\n\nاكتب من وين إلى وين وخل الكباتن يشوفون طلبك 🚘",
]

DRIVER_IDLE_MESSAGES = [
    "👨‍✈️ يا كباتن\n\nخلك قريب 🚗 يمكن ينزل الآن طلب يناسب خطك.",
    "🚘 يا أهل القيادة\n\nفيه عملاء ممكن يحتاجون مشاوير الآن، خلكم جاهزين 👨‍✈️",
    "👨‍✈️ الكابتن الجاهز يكسب الوقت.\n\nإذا أنت متوفر، تابع الطلبات الجديدة 🚗",
    "📍 كابتن؟\n\nخلك قريب من القروب، يمكن ينزل مشوار على خطك الآن 👀",
    "🚗 رزقك يمكن يكون بالطلب الجاي.\n\nخلك متابع يا كابتن 👨‍✈️",
]

GENERAL_IDLE_MESSAGES = [
    "🚗 القروب هادي شوي 😂\n\nاللي عنده مشوار يكتب من وين إلى وين، والكباتن موجودين 👨‍✈️",
    "👀 وين أهل المشاوير؟\n\nعميل يحتاج توصيل؟ كابتن ينتظر طلب؟ 🚘",
    "📍 مشوار جدة، مكة، الطائف أو أي منطقة؟\n\nاكتب طلبك والبوت يرتبه لك 🚗",
    "🤲 الله يرزق الجميع.\n\nعميل يحتاج مشوار؟ كابتن ينتظر رزقه؟ 🚘",
    "🚗 لا تخلي القروب ساكت 😂\n\nيمكن طلب بسيط يجيب رزق لكابتن اليوم.",
    "📢 أهل المشاوير والكباتن\n\nخلكم قريبين، يمكن الطلب الجاي يكون لكم 🚘",
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

    cur.execute("""
        INSERT OR IGNORE INTO settings(key, value)
        VALUES ('rules_text', '')
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

    if row:
        return row[0]

    return default


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

        return member.status in (
            "administrator",
            "creator"
        )

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
# GREETINGS
# =========================

GREETINGS = [
    "السلام عليكم ورحمة الله وبركاته",
    "السلام عليكم ورحمة الله",
    "السلام عليكم",
    "صباح الخير",
    "مساء الخير",
    "هلا والله",
    "هلا وغلا",
    "هلا",
    "يا هلا",
    "يا هلا والله",
]


def remove_greetings(text):
    text = clean_text(text)

    for greeting in GREETINGS:
        text = re.sub(
            re.escape(greeting),
            "",
            text,
            flags=re.IGNORECASE
        )

    return clean_text(text)


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
    "احتاج احد يوصلني",
    "ابغى احد يوصلني",
    "ابي احد يوصلني",
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
    "عندي مشوار من",
    "ابغى اروح من",
    "ابي اروح من",
    "مشوار من",
    "توصيل من",
]


KNOWN_LOCATIONS = [
    "جدة",
    "مكة",
    "مكه",
    "الطائف",
    "طايف",
    "أبحر",
    "ابحر",
    "الحمدانية",
    "الصفا",
    "النسيم",
    "المطار",
    "بحرة",
    "رابغ",
    "ثول",
    "الجموم",
    "المدينة",
    "الوزيرية",
    "المحجر",
    "مدائن الفهد",
    "الفيحاء",
    "النخيل",
    "الزهراء",
    "النيسان",
    "الصالحية",
    "القرينية",
    "الفضيلة",
    "القوزين",
]


def contains_known_location(text):
    lower = normalize_arabic(text)

    return any(
        normalize_arabic(location) in lower
        for location in KNOWN_LOCATIONS
    )


def looks_like_trip(text):
    text = clean_text(text)

    if not text:
        return False

    text_without_greeting = remove_greetings(text)
    normalized = normalize_arabic(text_without_greeting)

    for phrase in TRIP_PHRASES:
        if normalize_arabic(phrase) in normalized:
            return True

    if re.search(
        r"\bمن\b.+\b(?:الى|الي)\b",
        normalized
    ):
        return True

    if re.search(
        r"\bمن\b.+\bل+\b",
        normalized
    ):
        return True

    for separator in ["→", "->", ">", " - "]:
        if separator in text_without_greeting:
            parts = text_without_greeting.split(
                separator,
                1
            )

            if len(parts) == 2:
                if (
                    len(parts[0].strip()) >= 2
                    and len(parts[1].strip()) >= 2
                ):
                    return True

    if (
        "مين رايح" in normalized
        or "احد رايح" in normalized
        or "فيه احد رايح" in normalized
    ) and contains_known_location(text):
        return True

    return False


def extract_route(text):
    text = remove_greetings(text)
    normalized = normalize_arabic(text)

    match = re.search(
        r"من\s+(.+?)\s+(?:الى|الي)\s+(.+)",
        normalized
    )

    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip()
        )

    match = re.search(
        r"من\s+(.+?)\s+ل+\s*(.+)",
        normalized
    )

    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip()
        )

    for separator in ["→", "->", ">", " - "]:
        if separator in text:
            parts = text.split(
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
                    return start, destination

    return None, None


# =========================
# CREATE TRIP
# =========================

async def create_trip(message, context):
    customer = message.from_user

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
# LINKS
# =========================

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
    re.IGNORECASE
)


def forbidden_link(text):
    if not text:
        return False

    for link in URL_PATTERN.findall(text):
        link = link.rstrip(
            ".,!?؟،؛:)]}>\"'"
        )

        if link == ALLOWED_GROUP_LINK:
            continue

        if link.startswith(ALLOWED_GROUP_LINK):
            continue

        return True

    return False


# =========================
# FORWARDED MESSAGES
# =========================

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
    "متواجد بـ",
    "موجود في",
    "موجود ب",
    "موجود بـ",
    "انا في",
    "أنا في",
    "انا متواجد في",
    "أنا متواجد في",
    "متواجد حاليا في",
    "متواجد حاليًا في",
    "موجود حاليا في",
    "موجود حاليًا في",
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

    today = datetime.now(
        SAUDI_TZ
    ).date().isoformat()

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
        INSERT OR REPLACE INTO locations(
            user_id,
            last_date
        )
        VALUES (?, ?)
    """, (
        user.id,
        today
    ))

    con.commit()
    con.close()

    await message.reply_text(
        f"📍 تم تسجيل تواجد {display_user(user)}\n\n"
        f"📌 {html(text)}",
        parse_mode=ParseMode.HTML
    )

    return True


# =========================
# DRIVER
# =========================

DRIVER_READY_PHRASES = [
    "كابتن وجاهز",
    "كابتن جاهز",
    "انا كابتن",
    "أنا كابتن",
    "جاهز لاي مشوار",
    "جاهز لأي مشوار",
    "جاهز للمشاوير",
    "متوفر للمشاوير",
    "متوفر لأي مشوار",
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


async def handle_driver_ready(message, context):
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


# =========================
# VIOLATIONS
# =========================

BAD_WORDS = [
    "يا غبي",
    "يا حمار",
    "يا كلب",
    "يا تافه",
    "قليل الأدب",
    "قليل الادب",
    "انقلع",
]

INAPPROPRIATE = [
    "مين يبي يتعرف",
    "مين يبغى يتعرف",
    "ابغى بنت",
    "أبغى بنت",
    "ابغى وحدة",
    "أبغى وحدة",
    "تعالي معي",
]


def violation_reason(text):
    normalized = normalize_arabic(text)

    if normalized.strip() in (
        "خاص",
        "الخاص"
    ):
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

    row = cur.fetchone()
    count = row[0] if row else 1

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
            until = (
                datetime.now(SAUDI_TZ)
                + timedelta(hours=24)
            )

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
# READY BUTTON
# =========================

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

    if not driver:
        return

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
    custom = get_setting(
        "rules_text",
        ""
    )

    return custom if custom.strip() else DEFAULT_RULES


async def rules(update, context):
    await update.message.reply_text(
        get_rules()
    )


# =========================
# OWNER PANEL
# =========================

async def panel(update, context):
    user = update.effective_user

    if not is_owner(user):
        await update.message.reply_text(
            "🚫 هذا الأمر للمالك فقط."
        )

        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 الإحصائيات",
                callback_data="panel_stats"
            ),
            InlineKeyboardButton(
                "📋 القوانين",
                callback_data="panel_rules"
            )
        ],
        [
            InlineKeyboardButton(
                "⏱️ تشغيل التنشيط",
                callback_data="idle_on"
            ),
            InlineKeyboardButton(
                "⛔ إيقاف التنشيط",
                callback_data="idle_off"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 الأعضاء",
                callback_data="panel_users"
            )
        ]
    ])

    await update.message.reply_text(
        "👑 <b>لوحة تحكم المالك</b>\n\n"
        "اختر العملية:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def panel_buttons(update, context):
    query = update.callback_query

    await query.answer()

    user = query.from_user

    if not is_owner(user):
        await query.answer(
            "هذه اللوحة للمالك فقط.",
            show_alert=True
        )
        return

    data = query.data

    if data == "idle_on":
        set_setting(
            "idle_enabled",
            "1"
        )

        await query.edit_message_text(
            "✅ تم تشغيل رسائل تنشيط القروب.\n\n"
            "⏱️ سترسل بعد 30 دقيقة من الهدوء."
        )

        return

    if data == "idle_off":
        set_setting(
            "idle_enabled",
            "0"
        )

        await query.edit_message_text(
            "⛔ تم إيقاف رسائل تنشيط القروب."
        )

        return

    if data == "panel_rules":
        await query.message.reply_text(
            get_rules()
        )
        return

    if data == "panel_stats":
        con = db()
        cur = con.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM users"
        )
        users = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE is_driver = 1"
        )
        drivers = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM trips"
        )
        trips = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE violations > 0"
        )
        violations = cur.fetchone()[0]

        con.close()

        await query.message.reply_text(
            "📊 <b>إحصائيات القروب</b>\n\n"
            f"👥 الأعضاء المسجلون: {users}\n"
            f"👨‍✈️ الكباتن: {drivers}\n"
            f"🚗 إجمالي الطلبات: {trips}\n"
            f"⚠️ أعضاء عليهم مخالفات: {violations}",
            parse_mode=ParseMode.HTML
        )

        return

    if data == "panel_users":
        con = db()
        cur = con.cursor()

        cur.execute("""
            SELECT name, username, is_driver, violations
            FROM users
            ORDER BY rowid DESC
            LIMIT 15
        """)

        rows = cur.fetchall()
        con.close()

        text = "👥 <b>آخر الأعضاء المسجلين</b>\n\n"

        for row in rows:
            name = html(
                row[0] or "بدون اسم"
            )

            driver = "👨‍✈️" if row[2] else "👤"

            text += (
                f"{driver} {name} "
                f"⚠️ {row[3]}\n"
            )

        await query.message.reply_text(
            text,
            parse_mode=ParseMode.HTML
        )


# =========================
# BAN / MUTE
# =========================

def target_from_reply(update):
    message = update.message

    if not message:
        return None

    if not message.reply_to_message:
        return None

    return message.reply_to_message.from_user


async def ban_command(update, context):
    if not await is_admin(update, context):
        return

    target = target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "⚠️ رد على رسالة الشخص ثم اكتب /ban"
        )
        return

    if is_owner(target):
        await update.message.reply_text(
            "😂 ما تقدر تحظر المالك."
        )
        return

    try:
        await context.bot.ban_chat_member(
            GROUP_ID,
            target.id
        )

        await update.message.reply_text(
            f"🚫 تم حظر {target.full_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ تعذر الحظر:\n{e}"
        )


async def unban_command(update, context):
    if not await is_admin(update, context):
        return

    if not context.args:
        await update.message.reply_text(
            "الاستخدام:\n/unban USER_ID"
        )
        return

    try:
        user_id = int(
            context.args[0]
        )

        await context.bot.unban_chat_member(
            GROUP_ID,
            user_id,
            only_if_banned=True
        )

        await update.message.reply_text(
            "✅ تم فك الحظر."
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ تعذر فك الحظر:\n{e}"
        )


async def mute_command(update, context):
    if not await is_admin(update, context):
        return

    target = target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "⚠️ رد على رسالة الشخص ثم اكتب /mute"
        )
        return

    if is_owner(target):
        await update.message.reply_text(
            "😂 ما تقدر تكتم المالك."
        )
        return

    minutes = 60

    if context.args:
        try:
            minutes = int(
                context.args[0]
            )
        except Exception:
            pass

    until = (
        datetime.now(SAUDI_TZ)
        + timedelta(minutes=minutes)
    )

    try:
        await context.bot.restrict_chat_member(
            GROUP_ID,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            until_date=until
        )

        await update.message.reply_text(
            f"🔇 تم كتم {target.full_name} "
            f"لمدة {minutes} دقيقة."
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ تعذر الكتم:\n{e}"
        )


async def unmute_command(update, context):
    if not await is_admin(update, context):
        return

    target = target_from_reply(update)

    if not target:
        await update.message.reply_text(
            "⚠️ رد على رسالة الشخص ثم اكتب /unmute"
        )
        return

    try:
        await context.bot.restrict_chat_member(
            GROUP_ID,
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await update.message.reply_text(
            f"🔊 تم فك الكتم عن {target.full_name}."
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ تعذر فك الكتم:\n{e}"
        )


# =========================
# SET RULES
# =========================

async def setrules_command(update, context):
    if not is_owner(update.effective_user):
        await update.message.reply_text(
            "🚫 هذا الأمر للمالك فقط."
        )
        return

    text = " ".join(
        context.args
    ).strip()

    if not text:
        await update.message.reply_text(
            "الاستخدام:\n\n"
            "/setrules قوانينك الجديدة هنا"
        )
        return

    set_setting(
        "rules_text",
        text
    )

    await update.message.reply_text(
        "✅ تم تحديث قوانين القروب."
    )


async def resetrules_command(update, context):
    if not is_owner(update.effective_user):
        await update.message.reply_text(
            "🚫 هذا الأمر للمالك فقط."
        )
        return

    set_setting(
        "rules_text",
        ""
    )

    await update.message.reply_text(
        "✅ تم إرجاع القوانين الافتراضية."
    )


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
# CONVERSATION
# =========================

conversation_state = {}


def set_state(user_id, state):
    conversation_state[user_id] = {
        "state": state,
        "created": datetime.now(SAUDI_TZ)
    }


def get_state(user_id):
    data = conversation_state.get(user_id)

    if not data:
        return None

    age = (
        datetime.now(SAUDI_TZ)
        - data["created"]
    ).total_seconds()

    if age > 600:
        conversation_state.pop(
            user_id,
            None
        )
        return None

    return data["state"]


def clear_state(user_id):
    conversation_state.pop(
        user_id,
        None
    )


async def handle_single_trip_word(message, text):
    normalized = normalize_arabic(text)

    if normalized in [
        "مشوار",
        "توصيل",
        "مشوار؟",
        "توصيل؟",
    ]:
        set_state(
            message.from_user.id,
            "waiting_route"
        )

        await message.reply_text(
            "🚗 أبشر.\n\n"
            "اكتب لي من وين إلى وين؟\n\n"
            "مثال:\n"
            "📍 من الصفا إلى الحمدانية"
        )

        return True

    return False


async def handle_pending_trip(message, text):
    user = message.from_user

    if not user:
        return False

    if get_state(user.id) != "waiting_route":
        return False

    start, destination = extract_route(text)

    if start and destination:
        clear_state(user.id)

        await create_trip(
            message,
            None
        )

        return True

    await message.reply_text(
        "📍 اكتبها بهذا الشكل:\n\n"
        "من الموقع الأول إلى الموقع الثاني\n\n"
        "مثال: من أبحر إلى الحمدانية"
    )

    return True


# =========================
# SIMPLE RESPONSES
# =========================

RESPONSES = {
    "how_are_you": [
        "بخير دامك بخير 😎🚗",
        "تمام ولله الحمد 🌹",
        "الأمور طيبة يا أهل المشاوير 🚘",
    ],
    "news": [
        "علومنا طيبة دام أهل المشاوير موجودين 🚗",
        "كل الأمور طيبة ولله الحمد 🌹",
    ],
    "where": [
        "موجودين 😂🚗",
        "حاضرين، اللي عنده مشوار يكتب من وين إلى وين.",
    ],
    "thanks": [
        "الله يعافيك ويسعدك 🌹",
        "العفو يا الغالي 🚗",
        "الله يسعدك ويرزق الجميع 🤲",
    ],
    "hello": [
        "هلا والله 🌹🚗",
        "هلا وغلا، نورت القروب 👋",
        "يا هلا والله 🚘",
    ],
}


def classify_chat(text):
    normalized = normalize_arabic(text)

    if normalized in [
        "كيفكم",
        "كيف حالكم",
        "شلونكم",
        "وش اخباركم",
        "وش علومكم",
    ]:
        return "how_are_you"

    if normalized in [
        "وش الاخبار",
        "وش العلوم",
        "علومكم",
        "الاخبار",
    ]:
        return "news"

    if normalized in [
        "وينكم",
        "محد موجود",
        "احد موجود",
        "وين الكباتن",
    ]:
        return "where"

    if normalized in [
        "يعطيكم العافيه",
        "يعطيك العافيه",
        "الله يعافيكم",
        "الله يسعدكم",
        "مشكورين",
        "شكرا",
    ]:
        return "thanks"

    if normalized in [
        "هلا",
        "هلا والله",
        "هلا وغلا",
        "هلاا",
        "يا هلا",
    ]:
        return "hello"

    return None


async def smart_chat_response(message, text):
    category = classify_chat(text)

    if not category:
        return False

    await message.reply_text(
        random.choice(
            RESPONSES[category]
        )
    )

    return True


# =========================
# IDLE CHECKER
# =========================

async def idle_checker(context):
    global last_activity
    global last_idle_message
    global idle_turn

    if get_setting(
        "idle_enabled",
        "1"
    ) != "1":
        return

    now = datetime.now(
        SAUDI_TZ
    )

    idle_minutes = (
        now - last_activity
    ).total_seconds() / 60

    if idle_minutes < IDLE_MINUTES:
        return

    if idle_turn == 0:
        messages = CUSTOMER_IDLE_MESSAGES
    elif idle_turn == 1:
        messages = DRIVER_IDLE_MESSAGES
    else:
        messages = GENERAL_IDLE_MESSAGES

    choices = [
        message
        for message in messages
        if message != last_idle_message
    ]

    if not choices:
        choices = messages

    selected = random.choice(
        choices
    )

    try:
        await context.bot.send_message(
            GROUP_ID,
            selected
        )

        last_idle_message = selected

        idle_turn = (
            idle_turn + 1
        ) % 3

        last_activity = now

    except Exception as e:
        print(
            "Idle checker error:",
            e
        )


# =========================
# RULES BUTTON
# =========================

async def rules_button(update, context):
    query = update.callback_query

    await query.answer()

    if query.data == "rules":
        await query.message.reply_text(
            get_rules()
        )


# =========================
# MAIN MESSAGE HANDLER
# =========================

async def handle_message(update, context):
    global last_activity

    message = update.message

    if not message:
        return

    if not update.effective_chat:
        return

    if update.effective_chat.id != GROUP_ID:
        return

    if (
        message.from_user
        and message.from_user.is_bot
    ):
        return

    last_activity = datetime.now(
        SAUDI_TZ
    )

    user = message.from_user

    if not user:
        return

    save_user(user)

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    if await protect_content(
        update,
        context
    ):
        return

    reason = violation_reason(text)

    if reason:
        await violation(
            update,
            context,
            reason
        )
        return

    if await handle_driver_ready(
        message,
        context
    ):
        return

    if looks_like_trip(text):
        start, destination = extract_route(text)

        if start and destination:
            await create_trip(
                message,
                context
            )
            return

        set_state(
            user.id,
            "waiting_route"
        )

        await message.reply_text(
            "🚗 أبشر.\n"
            "بس اكتب لي من وين إلى وين؟\n\n"
            "مثال:\n"
            "📍 من الصفا إلى الحمدانية"
        )

        return

    if await handle_single_trip_word(
        message,
        text
    ):
        return

    if await handle_pending_trip(
        message,
        text
    ):
        return

    if await handle_location(
        update,
        context
    ):
        return

    if normalize_arabic(text) == "جاهز":
        if not message.reply_to_message:
            await message.reply_text(
                "⚠️ رد على رسالة المشوار أولًا "
                "ثم اكتب «جاهز»."
            )
            return

        mark_driver(user)

        await message.reply_text(
            f"👨‍✈️ {display_user(user)}\n"
            "تم تسجيلك ككابتن جاهز للمشوار ✅",
            parse_mode=ParseMode.HTML
        )

        return

    await smart_chat_response(
        message,
        text
    )


# =========================
# START
# =========================

async def start_command(update, context):
    await update.message.reply_text(
        f"🤖 {GROUP_NAME}\n\n"
        "✅ البوت يعمل.\n"
        "🚗 لخدمات المشاوير استخدم القروب."
    )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(update, context):
    print(
        "ERROR:",
        repr(context.error)
    )


# =========================
# MAIN
# =========================

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN غير موجود في GitHub Secrets"
        )

    init_db()

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome
        )
    )

    app.add_handler(
        CommandHandler(
            "rules",
            rules
        )
    )

    app.add_handler(
        CommandHandler(
            "panel",
            panel
        )
    )

    app.add_handler(
        CommandHandler(
            "ban",
            ban_command
        )
    )

    app.add_handler(
        CommandHandler(
            "unban",
            unban_command
        )
    )

    app.add_handler(
        CommandHandler(
            "mute",
            mute_command
        )
    )

    app.add_handler(
        CommandHandler(
            "unmute",
            unmute_command
        )
    )

    app.add_handler(
        CommandHandler(
            "setrules",
            setrules_command
        )
    )

    app.add_handler(
        CommandHandler(
            "resetrules",
            resetrules_command
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            ready_button,
            pattern=r"^ready:"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            rules_button,
            pattern=r"^rules$"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            panel_buttons,
            pattern=r"^(panel_|idle_)"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_error_handler(
        error_handler
    )

    if app.job_queue:
        app.job_queue.run_repeating(
            idle_checker,
            interval=60,
            first=60
        )

    print(
        f"🤖 {GROUP_NAME} يعمل الآن"
    )

    print(
        "⏱️ نظام تنشيط القروب: كل 30 دقيقة من الهدوء"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
