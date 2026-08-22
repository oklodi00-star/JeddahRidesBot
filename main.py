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

GROUP_NAME = "🚗 مشاوير جدة وضواحيها"

ADMIN_USERNAME = "klodi500"
OWNER_USERNAME = "klodi500"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "bot_data.db"

VIOLATION_RESET_DAYS = 30

MUTE_HOURS = 24


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في GitHub Secrets."
    )


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
                username TEXT DEFAULT '',
                is_driver INTEGER DEFAULT 0,
                is_customer INTEGER DEFAULT 0,
                violations INTEGER DEFAULT 0,
                last_violation_at TEXT,
                muted_until TEXT
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

        # -----------------------------
        # migrations
        # -----------------------------

        cur.execute("PRAGMA table_info(users)")
        user_columns = [
            row[1]
            for row in cur.fetchall()
        ]

        if "is_customer" not in user_columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN is_customer INTEGER DEFAULT 0
            """)

        if "last_violation_at" not in user_columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN last_violation_at TEXT
            """)

        if "muted_until" not in user_columns:
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN muted_until TEXT
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
# USER DATABASE
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


def is_driver(user_id):

    with db() as con:

        row = con.execute("""
            SELECT is_driver
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    return bool(row and row[0])


def is_customer(user_id):

    with db() as con:

        row = con.execute("""
            SELECT is_customer
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    return bool(row and row[0])


def get_username(user_id):

    with db() as con:

        row = con.execute("""
            SELECT username
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    return row[0] if row and row[0] else ""


def get_role(user_id):

    with db() as con:

        row = con.execute("""
            SELECT is_driver, is_customer
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

    if not row:
        return "unknown"

    if row[0]:
        return "driver"

    if row[1]:
        return "customer"

    return "unknown"


# ============================================================
# TEXT HELPERS
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
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ============================================================
# USER DISPLAY
# ============================================================

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


def user_badge(user_id):

    role = get_role(user_id)

    if role == "driver":
        return "👨‍✈️"

    if role == "customer":
        return "👤"

    return "👤"


def owner_display(user):

    if is_owner(user):
        return f"👑 {display_user(user)}"

    return f"{user_badge(user.id)} {display_user(user)}"


# ============================================================
# OWNER / ADMIN
# ============================================================

def is_owner(user):

    if not user:
        return False

    if user.username:
        if user.username.lower() == OWNER_USERNAME.lower():
            return True

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

        value, checked_at = cached

        if (
            now - checked_at
        ).total_seconds() < 300:

            return value

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
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب مخصص للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه بوضوح:
📍 من الحي → إلى الحي.

3️⃣ الكابتن الجاهز يضغط:
👨‍✈️ <b>جاهز للمشوار</b>

4️⃣ 🚫 ممنوع كتابة كلمة «خاص» في القروب.

5️⃣ 💰 السعر والتفاهم يكون بين العميل والكابتن بالخاص.

6️⃣ 🚫 يمنع السب أو الإساءة.

7️⃣ 🚫 يمنع نشر الإعلانات والروابط.

8️⃣ 🚫 الرسائل المحولة ممنوعة.

9️⃣ 📍 الكابتن يسمح له بإعلان تواجده مرة واحدة يوميًا.

🔟 🤝 الاحترام واجب على الجميع.

⚠️ <b>نظام المخالفات</b>

🟢 المخالفة الأولى: تنبيه.

🟡 المخالفة الثانية: تنبيه.

🟠 المخالفة الثالثة: كتم 24 ساعة.

🔴 المخالفة الرابعة وما بعدها: كتم 24 ساعة.

👑 إدارة القروب:
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
                    "👤 أنا عميل",
                    callback_data=f"role_customer:{member.id}",
                ),
                InlineKeyboardButton(
                    "👨‍✈️ أنا كابتن",
                    callback_data=f"role_driver:{member.id}",
                ),
            ],

            [
                InlineKeyboardButton(
                    "📋 القوانين",
                    callback_data="rules",
                ),
                InlineKeyboardButton(
                    "🛠️ الإدارة",
                    url=f"https://t.me/{ADMIN_USERNAME}",
                ),
            ],

            [
                InlineKeyboardButton(
                    "📩 شكاوى",
                    callback_data=f"complaint:{member.id}",
                ),
            ],
        ])

        await message.reply_text(
            f"👋 <b>يا هلا {owner_display(member)}</b>\n\n"
            f"نورت {GROUP_NAME} 🌹🚗\n\n"
            "عشان البوت يتعامل معك بشكل صحيح، "
            "حدد صفتك من الأزرار تحت 👇\n\n"
            "👤 العميل: يطلب مشوار.\n"
            "👨‍✈️ الكابتن: يأخذ المشاوير.\n\n"
            "بعد اختيارك، البوت بيعرفك تلقائيًا.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )


# ============================================================
# ROLE BUTTON
# ============================================================

async def role_selection_button(
    update,
    context,
):

    query = update.callback_query
    user = query.from_user

    try:

        role, target = (
            query.data.split(":", 1)
        )

        target = int(target)

    except Exception:

        await query.answer()
        return

    if user.id != target:

        await query.answer(
            "هذا الزر مخصص للعضو الجديد فقط 🙏",
            show_alert=True,
        )

        return

    if role == "role_driver":

        mark_driver(user)

        await query.answer(
            "تم تسجيلك ككابتن 👨‍✈️",
            show_alert=True,
        )

        await query.message.reply_text(
            f"👨‍✈️ {display_user(user)}\n\n"
            "تم تسجيلك ككابتن بنجاح ✅\n\n"
            "إذا شفت مشوار يناسبك، "
            "اضغط «جاهز للمشوار».\n\n"
            "📍 وتقدر تعلن تواجدك مرة واحدة يوميًا.",
            parse_mode=ParseMode.HTML,
        )

    elif role == "role_customer":

        mark_customer(user)

        await query.answer(
            "تم تسجيلك كعميل 👤",
            show_alert=True,
        )

        await query.message.reply_text(
            f"👤 {display_user(user)}\n\n"
            "تم تسجيلك كعميل بنجاح 🌹\n\n"
            "لطلب مشوار اكتب مثلًا:\n\n"
            "🚗 ابغى مشوار من الحمدانية إلى المطار\n\n"
            "والبوت بيحول كلامك تلقائيًا إلى بطاقة مشوار.",
            parse_mode=ParseMode.HTML,
        )


# ============================================================
# SMART TRIP UNDERSTANDING
# ============================================================

TRIP_WORDS = [
    "مشوار",
    "توصيل",
    "يوصلني",
    "يوديني",
    "اوصل",
    "اروح",
    "رايح",
    "رايحه",
    "كابتن",
    "تاكسي",
    "نقل",
    "ابي اروح",
    "ابغى اروح",
    "احتاج",
    "محتاج",
    "محتاجه",
    "ابي",
    "ابغى",
    "ابغا",
    "ودي",
    "ممكن",
]


def looks_like_trip(text):

    normalized = normalize_arabic(text)

    # طلب واضح
    has_trip_word = any(
        normalize_arabic(word) in normalized
        for word in TRIP_WORDS
    )

    # وجود مسار
    has_route = bool(
        re.search(
            r"\bمن\b.+\b(?:الى|إلى|الي|إلي)\b",
            text,
            re.IGNORECASE,
        )
    )

    has_arrow = (
        "→" in text
        or "->" in text
        or "➡️" in text
    )

    # كلمات صباح الخير وحدها ليست مشوار
    greetings_only = [
        "السلام عليكم",
        "السلام عليكم ورحمة الله",
        "هلا",
        "هلا والله",
        "اهلا",
        "اهلين",
        "صباح الخير",
        "مساء الخير",
    ]

    if normalized in [
        normalize_arabic(x)
        for x in greetings_only
    ]:
        return False

    # إذا فيه مسار فهو مشوار غالبًا
    if has_route or has_arrow:
        return True

    # إذا اجتمعت كلمة طلب مع مكان أو "من"
    if has_trip_word and (
        " من " in f" {normalized} "
        or " الى " in f" {normalized} "
        or "الي " in normalized
    ):
        return True

    # حالات مثل:
    # "السلام عليكم ابغى مشوار من..."
    if has_trip_word and len(normalized) > 18:
        return True

    return False


def extract_route(text):

    original = clean_text(text)

    # من X إلى Y
    match = re.search(
        r"(?:^|\s)من\s+(.+?)\s+(?:الى|إلى|الي|إلي)\s+(.+)$",
        original,
        re.IGNORECASE,
    )

    if match:

        start = match.group(1).strip()
        destination = match.group(2).strip()

        # إزالة عبارات زائدة
        destination = re.split(
            r"\s+(?:الساعه|الساعة|بسعر|بكم|كم)\b",
            destination,
            flags=re.IGNORECASE,
        )[0].strip()

        if start and destination:
            return start, destination

    # السهم
    for separator in [
        "→",
        "➡️",
        "->",
    ]:

        if separator in original:

            parts = original.split(
                separator,
                1,
            )

            if len(parts) == 2:

                left = parts[0].strip()
                right = parts[1].strip()

                # محاولة إزالة عبارة الطلب من البداية
                left = re.sub(
                    r"^(ابغى|ابغا|ابي|محتاج|احتاج|ودي|ممكن|مشوار|توصيل)\s*",
                    "",
                    left,
                    flags=re.IGNORECASE,
                )

                if len(left) >= 2 and len(right) >= 2:
                    return left, right

    return "", ""


# ============================================================
# TRIP CARD
# ============================================================

def trip_keyboard(trip_id):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "👨‍✈️ جاهز للمشوار",
                callback_data=f"ready:{trip_id}",
            ),
        ],

        [
            InlineKeyboardButton(
                "📩 عندي شكوى",
                callback_data=f"trip_complaint:{trip_id}",
            ),
        ],
    ])


async def create_trip(
    message,
    context,
):

    customer = message.from_user

    if not customer:
        return

    text = clean_text(
        message.text or ""
    )

    start, destination = extract_route(
        text
    )

    if start and destination:

        route = (
            f"📍 <b>من:</b> {html(start)}\n"
            f"🏁 <b>إلى:</b> {html(destination)}"
        )

    else:

        route = (
            "📍 <b>تفاصيل الطلب:</b>\n"
            f"{html(text)}"
        )

    # بطاقة أولية
    sent = await message.reply_text(
        "🚗 <b>طلب مشوار جديد</b>\n\n"
        f"👤 <b>العميل:</b> "
        f"{owner_display(customer)}\n\n"
        f"{route}\n\n"
        "👨‍✈️ الكابتن الجاهز يضغط "
        "«جاهز للمشوار».\n\n"
        "💰 السعر والتفاهم بالخاص.",
        parse_mode=ParseMode.HTML,
        reply_markup=trip_keyboard(0),
    )

    with db() as con:

        con.execute("""
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
            datetime.now(
                SAUDI_TZ
            ).isoformat(),
            start,
            destination,
            text,
        ))

        con.commit()

    await sent.edit_reply_markup(
        trip_keyboard(
            sent.message_id
        )
    )


# ============================================================
# READY
# ============================================================

READY_MESSAGES = [
    "رافقتك السلامة يا كابتن 🚗🌹",
    "الله يوفقك ويرزقك في مشوارك 🤲🚘",
    "تم تسجيلك يا كابتن، الله يعطيك خيره ويكفيك شره 🌹",
    "على بركة الله يا كابتن 🚗✨",
    "الله يكتب لك مشوار طيب ورزق مبارك 🤲",
    "تم يا كابتن 👨‍✈️ ربي يوفقك ويحفظك في طريقك.",
    "كفو يا كابتن 👌🚗 الله يرزقك بالمشوار الطيب.",
    "توكل على الله، رافقتك السلامة 🌹🚘",
]


async def ready_button(
    update,
    context,
):

    query = update.callback_query

    driver = query.from_user

    try:

        trip_id = int(
            query.data.split(":")[1]
        )

    except Exception:

        await query.answer()
        return

    if not driver:

        await query.answer()
        return

    # تسجيله ككابتن
    mark_driver(driver)

    with db() as con:

        cur = con.cursor()

        trip = cur.execute("""
            SELECT
                customer_id,
                customer_username,
                start,
                destination
            FROM trips
            WHERE message_id = ?
        """, (trip_id,)).fetchone()

        if not trip:

            await query.answer(
                "هذا المشوار غير موجود.",
                show_alert=True,
            )

            return

        customer_id = trip[0]
        customer_username = trip[1] or ""

        start = trip[2]
        destination = trip[3]

        already = cur.execute("""
            SELECT 1
            FROM ready
            WHERE trip_id = ?
            AND driver_id = ?
        """, (
            trip_id,
            driver.id,
        )).fetchone()

        if already:

            await query.answer(
                "أنت مسجل لهذا المشوار من قبل 😂",
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

    # الرسالة الخاصة بالكابتن
    await query.answer(
        random.choice(READY_MESSAGES),
        show_alert=True,
    )

    # رابط التواصل لا يظهر إلا عن طريق callback
    # ولا يستطيع استخدامه شخص لم يضغط جاهز
    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📩 تواصل مع العميل",
                callback_data=(
                    f"contact:{trip_id}:{driver.id}"
                ),
            ),
        ],

        [
            InlineKeyboardButton(
                "📞 تواصل مع الكابتن",
                callback_data=(
                    f"contactdriver:{customer_id}:{driver.id}"
                ),
            ),
        ],

    ])

    route = ""

    if start and destination:

        route = (
            f"\n📍 {html(start)}"
            f" → {html(destination)}"
        )

    await context.bot.send_message(
        chat_id=GROUP_ID,
        text=(
            "👨‍✈️ <b>كابتن جاهز للمشوار</b>\n\n"
            f"👨‍✈️ الكابتن: "
            f"{owner_display(driver)}"
            f"{route}\n\n"
            "💰 التفاهم والسعر بالخاص.\n\n"
            "🔐 أزرار التواصل مخصصة للأطراف المعنية فقط."
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        reply_to_message_id=trip_id,
    )


# ============================================================
# CONTACT CUSTOMER
# ============================================================

async def contact_customer_button(
    update,
    context,
):

    query = update.callback_query

    user = query.from_user

    try:

        _, trip_id, driver_id = (
            query.data.split(":")
        )

        trip_id = int(trip_id)
        driver_id = int(driver_id)

    except Exception:

        await query.answer()
        return

    # أهم حماية:
    # لازم يكون نفس الشخص الذي ضغط جاهز
    if user.id != driver_id:

        await query.answer(
            "العب غيرها يا حلو 😂\n"
            "هذا الزر للكابتن اللي ضغط جاهز فقط.",
            show_alert=True,
        )

        return

    with db() as con:

        row = con.execute("""
            SELECT
                customer_id,
                customer_username
            FROM trips
            WHERE message_id = ?
        """, (trip_id,)).fetchone()

        if not row:

            await query.answer(
                "المشوار غير موجود.",
                show_alert=True,
            )

            return

        customer_id = row[0]
        customer_username = row[1] or ""

        # تأكيد أنه ضغط جاهز فعلاً
        ready = con.execute("""
            SELECT 1
            FROM ready
            WHERE trip_id = ?
            AND driver_id = ?
        """, (
            trip_id,
            user.id,
        )).fetchone()

    if not ready:

        await query.answer(
            "العب غيرها يا حلو 😂",
            show_alert=True,
        )

        return

    # نحاول استخدام username
    if customer_username:

        await query.answer(
            f"📩 تواصل مع العميل:\n@{customer_username}",
            show_alert=True,
        )

        return

    # إذا ما عنده username
    await query.answer(
        "العميل ما عنده معرف تيليجرام ظاهر.\n"
        "تواصل معه من خلال القروب.",
        show_alert=True,
    )


# ============================================================
# CONTACT DRIVER
# ============================================================

async def contact_driver_button(
    update,
    context,
):

    query = update.callback_query

    user = query.from_user

    try:

        _, customer_id, driver_id = (
            query.data.split(":")
        )

        customer_id = int(customer_id)
        driver_id = int(driver_id)

    except Exception:

        await query.answer()
        return

    # فقط العميل صاحب الطلب
    if user.id != customer_id:

        await query.answer(
            "هذا الزر مخصص لصاحب الطلب فقط 🙏",
            show_alert=True,
        )

        return

    with db() as con:

        ready = con.execute("""
            SELECT 1
            FROM ready
            WHERE driver_id = ?
            LIMIT 1
        """, (driver_id,)).fetchone()

    if not ready:

        await query.answer(
            "الكابتن غير مسجل على أي مشوار.",
            show_alert=True,
        )

        return

    username = get_username(
        driver_id
    )

    if username:

        await query.answer(
            f"📞 تواصل مع الكابتن:\n@{username}",
            show_alert=True,
        )

    else:

        await query.answer(
            "الكابتن ما عنده username ظاهر.",
            show_alert=True,
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

    try:

        _, target_id = (
            query.data.split(":")
        )

        target_id = int(target_id)

    except Exception:

        await query.answer()
        return

    if user.id != target_id:

        await query.answer(
            "هذا الزر مخصص لصاحبه فقط 🙏",
            show_alert=True,
        )

        return

    await query.answer()

    await query.message.reply_text(
        f"🛠️ <b>الشكاوى والملاحظات</b>\n\n"
        f"{display_user(user)}\n"
        "إذا عندك شكوى أو مشكلة، تواصل مع الإدارة مباشرة:\n\n"
        f"👑 @{ADMIN_USERNAME}",
        parse_mode=ParseMode.HTML,
    )


async def trip_complaint(
    update,
    context,
):

    query = update.callback_query

    user = query.from_user

    try:

        _, trip_id = (
            query.data.split(":")
        )

        trip_id = int(trip_id)

    except Exception:

        await query.answer()
        return

    with db() as con:

        row = con.execute("""
            SELECT customer_id
            FROM trips
            WHERE message_id = ?
        """, (trip_id,)).fetchone()

    if not row:

        await query.answer(
            "المشوار غير موجود.",
            show_alert=True,
        )

        return

    if user.id != row[0]:

        await query.answer(
            "هذا الزر مخصص للعميل صاحب المشوار.",
            show_alert=True,
        )

        return

    await query.answer()

    await query.message.reply_text(
        f"🛠️ <b>شكوى العميل</b>\n\n"
        "إذا عندك مشكلة في المشوار أو مع الكابتن، "
        "تواصل مع الإدارة مباشرة:\n\n"
        f"👑 @{ADMIN_USERNAME}\n\n"
        "اكتب للإدارة تفاصيل المشكلة ووقت المشوار.",
        parse_mode=ParseMode.HTML,
    )


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

    # خاص
    if normalized.strip() in (
        "خاص",
        "الخاص",
    ):
        return "ممنوع كتابة خاص"

    # سب وإساءة
    for word in BAD_WORDS:

        if normalize_arabic(word) in normalized:
            return "إساءة أو سب"

    # كلام غير مناسب
    for phrase in INAPPROPRIATE:

        if normalize_arabic(phrase) in normalized:
            return "كلام غير مناسب"

    return None


# ============================================================
# VIOLATION HANDLER
# ============================================================

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

    if await is_admin(update, context):
        return

    # --------------------------------
    # خاص
    # --------------------------------

    if reason == "ممنوع كتابة خاص":

        try:
            await message.delete()
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=(
                f"⚠️ {owner_display(user)}\n\n"
                "🚫 <b>ممنوع كتابة «خاص»</b>\n\n"
                "إذا كنت كابتن وجاهز للمشوار "
                "اكتب «جاهز» أو اضغط زر "
                "«جاهز للمشوار» على بطاقة الطلب.\n\n"
                "🤖 خلنا نخلي القروب مرتب يا حلو 🌹"
            ),
            parse_mode=ParseMode.HTML,
        )

        # خاص محسوبة مخالفة
        reason = "ممنوع كتابة خاص"

    save_user(user)

    now = datetime.now(SAUDI_TZ)

    with db() as con:

        row = con.execute("""
            SELECT
                violations,
                last_violation_at
            FROM users
            WHERE user_id = ?
        """, (user.id,)).fetchone()

        violations = (
            row[0]
            if row
            else 0
        )

        last_violation = (
            row[1]
            if row
            else None
        )

        # تصفير المخالفات القديمة
        if last_violation:

            try:

                last_dt = datetime.fromisoformat(
                    last_violation
                )

                if (
                    now - last_dt
                ).days >= VIOLATION_RESET_DAYS:

                    violations = 0

            except Exception:
                pass

        count = violations + 1

        con.execute("""
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

    # --------------------------------
    # الرسائل
    # --------------------------------

    if count == 1:

        text = (
            f"🟢 <b>المخالفة رقم 1</b>\n\n"
            f"{owner_display(user)}\n"
            f"⚠️ السبب: {html(reason)}\n\n"
            "هذه المرة تنبيه فقط 🙏\n"
            "انتبه للقوانين."
        )

    elif count == 2:

        text = (
            f"🟡 <b>المخالفة رقم 2</b>\n\n"
            f"{owner_display(user)}\n"
            f"⚠️ السبب: {html(reason)}\n\n"
            "تنبيه أخير قبل الكتم 🔔\n"
            "المخالفة الثالثة = كتم 24 ساعة."
        )

    else:

        text = (
            f"🟠 <b>المخالفة رقم {count}</b>\n\n"
            f"{owner_display(user)}\n"
            f"⚠️ السبب: {html(reason)}\n\n"
            "🔇 سيتم كتمك لمدة 24 ساعة."
        )

    # --------------------------------
    # المخالفة الثالثة وما بعدها
    # --------------------------------

    if count >= 3:

        until = (
            datetime.now(SAUDI_TZ)
            + timedelta(hours=MUTE_HOURS)
        )

        try:

            await context.bot.restrict_chat_member(
                GROUP_ID,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                ),
                until_date=until,
            )

            with db() as con:

                con.execute("""
                    UPDATE users
                    SET muted_until = ?
                    WHERE user_id = ?
                """, (
                    until.isoformat(),
                    user.id,
                ))

                con.commit()

            text += (
                "\n\n🔇 <b>تم الكتم بنجاح لمدة 24 ساعة.</b>"
            )

        except Exception as error:

            logger.error(
                "Mute error: %s",
                error,
            )

            text += (
                "\n\n⚠️ تعذر تنفيذ الكتم، "
                "تأكد أن البوت لديه صلاحية تقييد الأعضاء."
            )

    await context.bot.send_message(
        GROUP_ID,
        text,
        parse_mode=ParseMode.HTML,
    )


# ============================================================
# PRICE DETECTION
# ============================================================

PRICE_PATTERN = re.compile(
    r"""
    (
        \b\d+\s*(?:ريال|ر\.س|رس)\b
        |
        \b(?:السعر|الاجره|الاجرة|كم السعر|بكم|بسعر)\b
        |
        \b\d+\s*(?:الى|-|إلى)\s*\d+\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def looks_like_public_price(text):

    normalized = normalize_arabic(text)

    price_words = [
        "السعر",
        "الاجره",
        "الاجره",
        "بكم",
        "كم السعر",
        "ريال",
        "ر.س",
    ]

    if any(
        normalize_arabic(x) in normalized
        for x in price_words
    ):
        return True

    if PRICE_PATTERN.search(text):
        return True

    return False


async def handle_public_price(
    update,
    context,
):

    message = update.message
    user = update.effective_user

    if not message or not user:
        return False

    if is_owner(user):
        return False

    if await is_admin(update, context):
        return False

    text = message.text or ""

    if not looks_like_public_price(text):
        return False

    try:
        await message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        GROUP_ID,
        (
            f"💰 {owner_display(user)}\n\n"
            "السعر والتفاهم يكون بالخاص بين العميل والكابتن 🤝\n"
            "🚫 ممنوع نشر الأسعار في القروب."
        ),
        parse_mode=ParseMode.HTML,
    )

    return True


# ============================================================
# LINKS / FORWARDS
# ============================================================

URL_PATTERN = re.compile(
    r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
    re.IGNORECASE,
)


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

    if await is_admin(update, context):
        return False

    # الرسائل المحولة
    if is_forwarded(message):

        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {owner_display(user)}\n\n"
            "🚫 الرسائل المحولة ممنوعة.\n"
            "اكتب رسالتك مباشرة.",
            parse_mode=ParseMode.HTML,
        )

        return True

    text = (
        message.text
        or message.caption
        or ""
    )

    # الروابط
    if URL_PATTERN.search(text):

        try:
            await message.delete()
        except Exception:
            pass

        await message.reply_text(
            f"⚠️ {owner_display(user)}\n\n"
            "🚫 الروابط ممنوعة في القروب.",
            parse_mode=ParseMode.HTML,
        )

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
    "انا متواجد في",
    "متواجد حاليا في",
    "موجود حاليا في",
    "متواجد حاليا ب",
]


def is_location(text):

    normalized = normalize_arabic(text)

    return any(
        normalize_arabic(phrase) in normalized
        for phrase in LOCATION_PHRASES
    )


async def handle_location(
    update,
    context,
):

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
            "إذا أنت كابتن اختر «أنا كابتن» أولًا."
        )

        return True

    today = datetime.now(
        SAUDI_TZ
    ).date().isoformat()

    with db() as con:

        row = con.execute("""
            SELECT last_date
            FROM locations
            WHERE user_id = ?
        """, (user.id,)).fetchone()

        if row and row[0] == today:

            already = True

        else:

            already = False

            con.execute("""
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
            "😂 يا كابتن عرفنا وينك اليوم.\n\n"
            "📍 إعلان التواجد مسموح مرة واحدة فقط يوميًا."
        )

        return True

    await message.reply_text(
        f"📍 <b>تم تسجيل تواجدك يا كابتن</b>\n\n"
        f"{owner_display(user)}\n\n"
        "🚗 تم تسجيل موقع تواجدك اليوم.\n"
        "⏳ انتظر مشوارك، والله يرزقك من واسع فضله 🤲🌹",
        parse_mode=ParseMode.HTML,
    )

    return True


# ============================================================
# SMART GREETINGS
# ============================================================

GREETING_RESPONSES = {

    "السلام": [
        "وعليكم السلام ورحمة الله وبركاته 🌹🚗",
        "وعليكم السلام يا هلا والله 👋",
        "وعليكم السلام، نورت القروب 🚘🌹",
    ],

    "هلا": [
        "هلا وغلا 👋🚗",
        "يا هلا والله 🌹",
        "هلا بك يا الغالي 🚘",
    ],

    "اهلا": [
        "أهلين وسهلين 🌹",
        "يا مرحبا 👋🚗",
    ],

    "صباح": [
        "صباح النور والرزق 🌹🚗",
        "صباحكم خير وبركة 🤲",
    ],

    "مساء": [
        "مساء النور 🌙🌹",
        "مساءكم خير يا أهل المشاوير 🚗",
    ],

    "شكرا": [
        "العفو يا الغالي 🌹",
        "حاضرين 🚗",
        "تستاهل كل خير ❤️",
    ],

    "مشكور": [
        "العفو يا الغالي 🌹",
        "حاضرين وما سوينا إلا الواجب 🚗",
    ],

    "يعطيك العافيه": [
        "الله يعافيك ويسعدك 🌹",
        "وياك يا رب 🤲",
    ],

    "وينكم": [
        "موجودين يا الغالي 😂🚗",
        "حاضرين، تفضل 👋",
    ],

    "احد موجود": [
        "موجودين يا الغالي 🚗",
        "حاضرين، تفضل 👋",
    ],
}


def get_greeting(text):

    normalized = normalize_arabic(text)

    # لا نرد على التحية إذا كانت داخل بطاقة مشوار
    if looks_like_trip(text):
        return None

    for key, responses in GREETING_RESPONSES.items():

        if normalize_arabic(key) in normalized:

            return random.choice(
                responses
            )

    return None


async def handle_smart_chat(message):

    text = message.text or ""

    response = get_greeting(text)

    if not response:
        return False

    await message.reply_text(
        response
    )

    return True


# ============================================================
# DRIVER READY TEXT
# ============================================================

READY_TEXTS = [
    "جاهز",
    "كابتن جاهز",
    "انا كابتن وجاهز",
    "أنا كابتن وجاهز",
    "جاهز للمشاوير",
    "متوفر للمشاوير",
]


def is_driver_ready_text(text):

    normalized = normalize_arabic(text)

    for phrase in READY_TEXTS:

        if normalized == normalize_arabic(phrase):
            return True

    return False


async def handle_driver_ready_text(
    message,
):

    user = message.from_user

    if not user:
        return False

    if not is_driver_ready_text(
        message.text or ""
    ):
        return False

    mark_driver(user)

    await message.reply_text(
        f"👨‍✈️ {owner_display(user)}\n\n"
        "✅ تم تسجيلك ككابتن.\n\n"
        "🚗 إذا كنت تقصد مشوارًا معينًا، "
        "اضغط «جاهز للمشوار» من بطاقة المشوار نفسها.\n\n"
        "📍 وإذا تبي تعلن تواجدك اكتب:\n"
        "متواجد في الحمدانية",
        parse_mode=ParseMode.HTML,
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

    # حماية الروابط والتحويل
    if await protect_message(
        update,
        context,
    ):
        return

    text = message.text or ""

    if not text:
        return

    # المخالفات أولًا
    reason = violation_reason(text)

    if reason:

        await handle_violation(
            update,
            context,
            reason,
        )

        return

    # السعر في العام
    if await handle_public_price(
        update,
        context,
    ):
        return

    # طلب المشوار
    if looks_like_trip(text):

        # لا نعامل تحية + طلب كتحية
        await create_trip(
            message,
            context,
        )

        return

    # جاهز كنص
    if await handle_driver_ready_text(
        message
    ):
        return

    # موقع الكابتن
    if await handle_location(
        update,
        context,
    ):
        return

    # الذكاء في التحية
    if await handle_smart_chat(
        message
    ):
        return


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

    if data == "rules":

        await query.answer()

        await query.message.reply_text(
            RULES,
            parse_mode=ParseMode.HTML,
        )

        return

    if data.startswith("role_customer:"):

        await role_selection_button(
            update,
            context,
        )

        return

    if data.startswith("role_driver:"):

        await role_selection_button(
            update,
            context,
        )

        return

    if data.startswith("ready:"):

        await ready_button(
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

    if data.startswith("trip_complaint:"):

        await trip_complaint(
            update,
            context,
        )

        return

    await query.answer()


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
        f"🚗 <b>{GROUP_NAME}</b>\n\n"
        "🤖 البوت يعمل بنجاح ✅\n\n"
        "📋 /rules — القوانين\n"
        "ℹ️ /help — المساعدة",
        parse_mode=ParseMode.HTML,
    )


async def rules(
    update,
    context,
):

    if not update.message:
        return

    await update.message.reply_text(
        RULES,
        parse_mode=ParseMode.HTML,
    )


async def help_command(
    update,
    context,
):

    if not update.message:
        return

    await update.message.reply_text(
        f"""
🤖 <b>طريقة استخدام {GROUP_NAME}</b>

👤 <b>للعميل:</b>

اكتب طلبك بشكل طبيعي، مثل:

🚗 ابغى مشوار من الحمدانية إلى المطار

أو:

السلام عليكم، احتاج أحد يوديني من الصفا إلى التحلية

والبوت يفهم أنك تطلب مشوار ويحول رسالتك إلى بطاقة طلب.

👨‍✈️ <b>للكابتن:</b>

إذا شفت طلب يناسبك اضغط:

«جاهز للمشوار»

🔐 بعدها فقط الكابتن الذي ضغط جاهز يستطيع استخدام زر التواصل مع العميل.

📍 لإعلان التواجد:

متواجد في الحمدانية

💰 السعر والتفاهم بالخاص.

🚫 ممنوع كتابة «خاص» في القروب.

🛠️ الشكاوى:
من زر الشكاوى أو تواصل مع الإدارة.
""",
        parse_mode=ParseMode.HTML,
    )


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
        "🚗 مشاوير جدة وضواحيها",
        flush=True,
    )

    print(
        "🤖 Starting Smart Telegram Bot...",
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

    # Commands
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

    # Welcome
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            welcome,
        )
    )

    # Buttons
    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # Text
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

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
