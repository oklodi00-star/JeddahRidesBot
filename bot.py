"""
🤖 بوت مشاوير جدة الذكي - النسخة المصححة

التعديلات:
- إصلاح نمط كلمات الاتجاه
- إصلاح تكرار المواقع
- إصلاح فلتر كلمة خاص
- إصلاح فلتر الروابط
- إصلاح كشف التواجد
- إصلاح كتم المخالفات (إضافة جدول banned_users)
- إصلاح عداد المخالفات (تصفير بعد الكتم)
- إضافة الرد النصي "جاهز"
- إضافة إلغاء الطلب المعلق
- الإبقاء على زر "جاهز" كما هو (بدون تقفيل الطلب)
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
    ChatMemberHandler,
    ContextTypes,
    filters,
)


# ============================================================
# ⚙️ الإعدادات
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "").strip()

GROUP_ID = -1003716441020

GROUP_NAME = "🚘 مشاوير جدة وضواحيها"

ADMIN_USERNAME = "klodi500"

ADMIN_IDS = [
    952638746
]

ALLOWED_GROUP_LINK = "t.me/JeddahRidesGroup"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides.db"


# ============================================================
# 📋 رسالة الترحيب
# ============================================================

WELCOME_TEXT = f"""
🎉 <b>أهلاً وسهلاً بك في {GROUP_NAME}</b>

🚘 المجموعة مخصصة للمشاوير داخل جدة وضواحيها.

━━━━━━━━━━━━━━━━━━

👤 <b>طريقة طلب مشوار:</b>

اكتب طلبك مباشرة في القروب، مثلاً:

«من الفضيلة إلى الأندلس الساعة 5 مساءً»

أو:

«من الحرازات إلين تيسير»

🤖 سيقوم البوت بتسجيل الطلب.

━━━━━━━━━━━━━━━━━━

🚕 <b>طريقة الكابتن:</b>

إذا كنت جاهزاً لتنفيذ أحد الطلبات:

اضغط زر «🚕 جاهز»

أو اقتبس طلب العميل واكتب:

«جاهز»

━━━━━━━━━━━━━━━━━━

📍 <b>إعلان التواجد:</b>

مثلاً:

«متواجد في الفضيلة»

أو:

«متواجد بالحرازات لأي مشوار»

⚠️ يسمح بتسجيل التواجد مرة واحدة يومياً.

━━━━━━━━━━━━━━━━━━

🚫 <b>مهم:</b>

ممنوع كتابة «خاص».

ممنوع نشر أرقام الجوال.

ممنوع نشر الروابط الخارجية.

التواصل يكون عن طريق أزرار البوت فقط.
"""


# ============================================================
# 📚 الكلمات
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "شهرية", "شهريه", "شهرياً", "شهريا", "بالشهر",
    "دوام", "مدرسه", "مدرسة", "جامعه", "جامعة", "التزام",
    "اسبوعي", "أسبوعي", "يومي", "يوميا", "يومياً", "مشوار يومي", "توصيل يومي",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "مشاوير", "توصيل", "توصيله", "توصيلة", "يوصلني", "يوديني",
    "ابغى مشوار", "ابي مشوار", "أبي مشوار", "ابغا مشوار", "أبغا مشوار",
    "احتاج توصيل", "أحتاج توصيل", "محتاج توصيل", "محتاجة توصيل",
    "من يوصلني", "اوصلني", "أوصلني", "ودني", "خذني", "ابي اروح",
    "أبي أروح", "ابغى اروح", "أبغى اروح", "ابغا اروح", "اريد مشوار",
]

PRESENCE_PHRASES = [
    "متواجد", "متواجدة", "متواجده", "متواجدين", "متواجدون",
    "متواجدين في", "متواجدين بـ", "متواجدين ب", "متوفر", "متوفرة",
    "متوفره", "متاح", "متاحة", "متاحه", "انا في", "أنا في",
    "انا عند", "أنا عند", "واقف", "واقفة", "واقفه", "في الموقع",
    "بالخدمة", "بالخدمه",
]

PRESENCE_QUESTION_WORDS = [
    "مين", "من", "وين", "احد", "أحد", "فيه احد", "فيه أحد",
    "في احد", "في أحد", "الموجودين", "موجودين", "المتواجدين",
    "متواجدين", "الموجود", "موجود",
]

LOCATIONS = [
    "الحرازات الشمالية", "الحرازات الجنوبية", "الأندلس مول", "الاندلس مول",
    "الفضيلة", "الفضيله", "الرغامة", "الرغامه", "الخمرة", "الخمره",
    "الوزيرية", "الوزيريه", "السنابل", "التيسير", "تيسير", "الحرازات",
    "النسيم", "الأندلس", "الاندلس", "الصناعية", "الزهراء", "النخيل",
    "الصالحية", "الروضة", "الصفا", "المروة", "الجامعة", "الحمراء",
    "الربوة", "النزهة", "المشرفة", "بني مالك", "الحمدانية", "المحمدية",
    "الخالدية", "النعيم", "السلامة", "الشاطئ", "أبحر", "ابحر",
    "التوفيق", "العدل", "المنار", "الواحة", "الفيصلية", "الريان",
    "الوادي", "الفلاح", "النهضة", "الرابية", "السلام", "المرجان",
    "الكورنيش", "الصالة", "الفيحاء", "مكة", "جدة",
]

# تم إصلاح النمط ليتوافق مع النص المطبع (إزالة الهمزات)
TO_WORDS_PATTERN = r"(?:الى|الي|الين|لين|الا|ل|to)"

GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام",
    "صباح الخير", "مساء الخير", "هلا", "اهلا", "أهلا", "مرحبا",
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

        # تم إصلاح جدول الحظر ليشمل تاريخ الانتهاء
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                until_date TEXT,
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
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                username = excluded.username
        """, (
            user.id, user.full_name, user.username or "",
            datetime.now(SAUDI_TZ).isoformat()
        ))
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
        cur.execute("SELECT until_date FROM banned_users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return False
        
        until_date = datetime.fromisoformat(row["until_date"])
        if datetime.now(SAUDI_TZ) > until_date:
            # انتهت مدة الحظر، نقوم بإزالته
            cur.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return False
        return True

    def ban_user(self, user_id, reason, hours=24):
        cur = self.conn.cursor()
        until_date = (datetime.now(SAUDI_TZ) + timedelta(hours=hours)).isoformat()
        cur.execute("""
            INSERT INTO banned_users (user_id, reason, until_date, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                reason = excluded.reason,
                until_date = excluded.until_date
        """, (user_id, reason, until_date, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()

    def create_trip(self, message_id, customer_id, customer_name, pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, customer_name, pickup, destination, trip_type, original_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id, customer_id, customer_name, pickup, destination,
            trip_type, original_text, datetime.now(SAUDI_TZ).isoformat()
        ))
        self.conn.commit()
        return cur.lastrowid

    def get_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_trip_by_message_id(self, message_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE message_id = ? AND status = 'active'", (message_id,))
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

    def add_violation(self, user_id, reason):
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM violations WHERE user_id = ?", (user_id,))
        row = cur.fetchone()

        if row:
            count = row["count"] + 1
            cur.execute("""
                UPDATE violations SET count = ?, last_reason = ?, updated_at = ? WHERE user_id = ?
            """, (count, reason, datetime.now(SAUDI_TZ).isoformat(), user_id))
        else:
            count = 1
            cur.execute("""
                INSERT INTO violations (user_id, count, last_reason, updated_at) VALUES (?, ?, ?, ?)
            """, (user_id, count, reason, datetime.now(SAUDI_TZ).isoformat()))

        self.conn.commit()
        return count

    def reset_violations(self, user_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE violations SET count = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

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
            ON CONFLICT(user_id) DO UPDATE SET
                location = excluded.location,
                last_date = excluded.last_date,
                updated_at = excluded.updated_at
        """, (user_id, location, today, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()


# ============================================================
# 🤖 البوت
# ============================================================

class SmartRidesBot:

    def __init__(self):
        self.db = Database()
        self.pending_trips = {}
        self.welcomed_members = set()

    def normalize_text(self, text):
        if not text:
            return ""
        text = str(text).lower()
        text = text.replace("ـ", "")  # إزالة التطويل
        replacements = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي",
            "ة": "ه", "ؤ": "و", "ئ": "ي",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
        return text

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def strip_greetings(self, text):
        if not text:
            return ""
        cleaned = text
        for greeting in sorted(GREETINGS, key=len, reverse=True):
            cleaned = re.sub(re.escape(greeting), " ", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

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
        return any(re.search(pattern, compact) for pattern in patterns)

    def contains_private_word(self, text):
        normalized = self.normalize_text(text)
        words = re.findall(r"[\w\u0600-\u06FF]+", normalized)
        # تم إضافة الصيغ المطبوعة لمنع التحايل
        forbidden = {
            "خاص", "بالخاص", "للخاص", "خاصني", "خاصك",
            "خاصه", "بالخاصه", "للخاصه",
        }
        return any(word in forbidden for word in words)

    def contains_unauthorized_link(self, text):
        if not text:
            return False
        links = re.findall(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)", text.lower())
        for link in links:
            # تم إصلاح المقارنة لتتجاهل https://
            if ALLOWED_GROUP_LINK.lower() in link.replace("https://", "").replace("http://", ""):
                continue
            return True
        return False

    def extract_route(self, text):
        if not text:
            return None, None

        normalized = self.normalize_text(text)
        pattern1 = rf"من\s+(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)"
        match = re.search(pattern1, normalized, re.IGNORECASE)

        if match:
            pickup = match.group(1).strip()
            destination = match.group(2).strip()
            pickup = re.sub(r"[.!،,؟?]+$", "", pickup).strip()
            destination = re.sub(r"[.!،,؟?]+$", "", destination).strip()
            destination = re.sub(r"\s+(?:الساعه|الساعة|بعد|قبل)\s+.*$", "", destination).strip()
            if pickup and destination:
                return pickup, destination

        pattern2 = rf"^(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)"
        match = re.search(pattern2, normalized, re.IGNORECASE)

        if match:
            pickup = match.group(1).strip()
            destination = match.group(2).strip()
            pickup = re.sub(r"[.!،,؟?]+$", "", pickup).strip()
            destination = re.sub(r"[.!،,؟?]+$", "", destination).strip()
            if pickup and destination:
                return pickup, destination

        # تم إصلاح التكرار باستخدام set
        found = []
        found_normalized = set()

        for location in sorted(LOCATIONS, key=lambda x: len(self.normalize_text(x)), reverse=True):
            normalized_location = self.normalize_text(location)
            if normalized_location in normalized:
                if normalized_location not in found_normalized:
                    found_normalized.add(normalized_location)
                    found.append(location)

        if len(found) >= 2:
            return found[0], found[1]

        return None, None

    def detect_trip(self, text):
        clean_text = self.strip_greetings(text)
        normalized = self.normalize_text(clean_text)

        pickup, destination = self.extract_route(clean_text)

        has_intent = any(
            self.normalize_text(word) in normalized
            for word in (NORMAL_TRIP_WORDS + MONTHLY_TRIP_WORDS)
        )
        has_route = bool(pickup and destination)
        route_pattern = re.search(rf"من\s+.+?\s+{TO_WORDS_PATTERN}\s+.+", normalized, re.IGNORECASE)
        
        if route_pattern:
            has_route = True

        if not has_intent and not has_route:
            return None, None, None

        monthly = any(self.normalize_text(word) in normalized for word in MONTHLY_TRIP_WORDS)
        trip_type = "monthly" if monthly else "normal"
        return trip_type, pickup, destination

    def detect_presence(self, text):
        if not text:
            return None

        clean_text = self.strip_greetings(text)
        normalized = self.normalize_text(clean_text)
        question_normalized = normalized
        question_detected = False

        for word in PRESENCE_QUESTION_WORDS:
            normalized_word = self.normalize_text(word)
            if re.search(rf"(^|\s){re.escape(normalized_word)}(\s|$)", question_normalized):
                question_detected = True
                break

        if question_detected:
            if re.search(r"(^|\s)(مين|من|الموجودين|موجودين|المتواجدين)(\s|$)", question_normalized):
                return None

        presence_patterns = [
            r"(^|\s)متواجد(\s|$)", r"(^|\s)متواجده(\s|$)", r"(^|\s)متواجدة(\s|$)",
            r"(^|\s)متوفر(\s|$)", r"(^|\s)متوفره(\s|$)", r"(^|\s)متوفرة(\s|$)",
            r"(^|\s)متاح(\s|$)", r"(^|\s)متاحه(\s|$)", r"(^|\s)متاحة(\s|$)",
            r"(^|\s)انا\s+في(\s|$)", r"(^|\s)انا\s+عند(\s|$)",
            r"(^|\s)واقف(\s|$)", r"(^|\s)واقفه(\s|$)", r"(^|\s)واقفة(\s|$)",
            r"(^|\s)في\s+الموقع(\s|$)", r"(^|\s)بالخدمه(\s|$)", r"(^|\s)بالخدمة(\s|$)",
        ]

        has_presence = any(re.search(pattern, normalized) for pattern in presence_patterns)

        if not has_presence:
            return None

        for location in sorted(LOCATIONS, key=lambda x: len(self.normalize_text(x)), reverse=True):
            normalized_location = self.normalize_text(location)
            if normalized_location in normalized:
                return location

        patterns = [
            r"(?:في|عند)\s+([^\s،,.!?؟]+)",
            # تم إزالة النمط العشوائي r"\bب(...)" واستبداله بنمط أكثر تحديداً
            r"\bب([^\s،,.!?؟]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                location = match.group(1).strip()
                if location in {"اي", "أي", "مشوار", "مشاوير", "الموقع"}:
                    continue
                # التأكد من أن الكلمة الملتقطة هي موقع معروف أو ليست فعل
                if any(self.normalize_text(loc) == location for loc in LOCATIONS):
                    return location

        location_text = normalized
        remove_phrases = [
            "متواجد", "متواجده", "متواجدة", "متوفر", "متوفره", "متوفرة",
            "متاح", "متاحه", "متاحة", "انا", "في", "عند", "واقف", "واقفه",
            "واقفة", "بالخدمه", "بالخدمة", "لأي مشوار", "لاي مشوار",
            "لاي مشاوير", "لأي مشاوير", "للمشاوير", "للمشوار",
        ]

        for phrase in sorted(remove_phrases, key=len, reverse=True):
            location_text = location_text.replace(self.normalize_text(phrase), " ")

        location_text = re.sub(r"\s+", " ", location_text).strip()

        if location_text:
            words = location_text.split()
            if words:
                return words[0]

        return ""

    async def delete_message(self, message):
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"تعذر حذف الرسالة: {e}")

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
        if user.id in ADMIN_IDS:
            return

        count = self.db.add_violation(user.id, reason)
        await self.delete_message(message)

        if count == 1:
            text = (
                f"⚠️ <b>تنبيه</b>\n\n"
                f"يا {self.html(user.first_name)}، "
                f"تم تسجيل المخالفة الأولى.\n"
                f"السبب: {self.html(reason)}"
            )
        elif count == 2:
            text = (
                f"⚠️ <b>تحذير أخير</b>\n\n"
                f"يا {self.html(user.first_name)}، "
                f"تم تسجيل المخالفة الثانية.\n\n"
                f"⚠️ الثالثة = كتم 24 ساعة."
            )
        else:
            text = (
                f"🚫 <b>تم كتمك لمدة 24 ساعة</b>\n\n"
                f"السبب: {self.html(reason)}"
            )

        try:
            warning = await context.bot.send_message(
                chat_id=message.chat_id, text=text, parse_mode=ParseMode.HTML
            )
            if context.job_queue:
                context.job_queue.run_once(self.delete_later, 8, data=warning)
        except Exception as e:
            logger.error(f"خطأ في إرسال التحذير: {e}")

        if count >= 3:
            try:
                until_date = datetime.now(SAUDI_TZ) + timedelta(hours=24)
                await context.bot.restrict_chat_member(
                    chat_id=message.chat_id,
                    user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                # تم إصلاح كتم المخالفات: تسجيله في قاعدة البيانات
                self.db.ban_user(user.id, reason, hours=24)
                # تم إصلاح العداد: تصفيره بعد الكتم
                self.db.reset_violations(user.id)
            except Exception as e:
                logger.error(f"خطأ في الكتم: {e}")

    async def send_welcome(self, context, member):
        if member.id in self.welcomed_members:
            return
        self.welcomed_members.add(member.id)

        try:
            self.db.save_user(member)
        except Exception as e:
            logger.error(f"فشل حفظ المستخدم: {e}")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"👤 {member.first_name} عميل", callback_data=f"btn_customer:{member.id}"),
                InlineKeyboardButton(f"🚕 {member.first_name} كابتن", callback_data=f"btn_driver:{member.id}")
            ],
            [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")]
        ])

        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=WELCOME_TEXT + "\n\n" + f"👋 انضم: <b>{self.html(member.first_name)}</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"فشل إرسال الترحيب: {e}")

    async def handle_chat_member(self, update, context):
        cm = update.chat_member
        if not cm:
            return
        if cm.chat.id != GROUP_ID:
            return

        old_status = cm.old_chat_member.status
        new_status = cm.new_chat_member.status

        if old_status in ("left", "kicked") and new_status in ("member", "restricted"):
            user = cm.new_chat_member.user
            if user.is_bot:
                return
            await self.send_welcome(context, user)

    async def handle_presence(self, update, context, location):
        message = update.effective_message
        user = update.effective_user
        if not message or not user:
            return

        self.db.save_user(user)

        if self.db.get_presence_today(user.id):
            await self.issue_violation(update, context, "تكرار إعلان التواجد أكثر من مرة في اليوم")
            return

        self.db.save_presence(user.id, location)

        await message.reply_text(
            f"📍 <b>تم تسجيل تواجدك</b>\n\n"
            f"🚕 الكابتن: {self.html(user.first_name)}\n"
            f"📍 الموقع: {self.html(location)}",
            parse_mode=ParseMode.HTML
        )

    async def handle_trip(self, update, context, trip_type, pickup, destination):
        message = update.effective_message
        user = update.effective_user
        if not message or not user:
            return

        self.db.save_user(user)
        self.db.set_role(user.id, "customer")

        if not pickup or not destination:
            self.pending_trips[user.id] = {
                "type": trip_type, "pickup": pickup, "destination": destination,
            }

            if not pickup and not destination:
                question = (
                    "📍 <b>من وين إلى وين؟</b>\n\n"
                    "مثال:\n«من الحرازات إلين تيسير»"
                )
            elif not pickup:
                question = f"📍 <b>ما زال ناقص: من وين تنطلق؟</b>\n\n🏁 الوصول: {self.html(destination)}"
            else:
                question = f"🏁 <b>ما زال ناقص: إلى وين رايح؟</b>\n\n📍 الانطلاق: {self.html(pickup)}"

            await message.reply_text(question, parse_mode=ParseMode.HTML)
            return

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

        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"

        await message.reply_text(
            f"✅ <b>تم تسجيل طلبك</b>\n\n"
            f"📋 النوع: {type_badge}\n"
            f"📍 من: {self.html(pickup)}\n"
            f"🏁 إلى: {self.html(destination)}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

    async def process_take_trip(self, context, user, trip, from_query=None):
        """دالة موحدة لمعالجة طلب الجاهزية (سواء من الزر أو الرد النصي)"""
        if user.id == trip["customer_id"]:
            if from_query:
                await from_query.answer("😂 لا يمكنك أخذ مشوارك بنفسك.", show_alert=True)
            return

        self.db.save_user(user)
        self.db.set_role(user.id, "driver")

        added = self.db.add_ready_driver(
            trip["trip_id"], user.id, user.first_name or "الكابتن"
        )

        if not added:
            if from_query:
                await from_query.answer("⚠️ أنت مسجل بالفعل لهذا المشوار.", show_alert=True)
            return

        if from_query:
            await from_query.answer("✅ تم تسجيل جاهزيتك.", show_alert=True)

        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(
                    f"🚕 <b>تم تسجيل كابتن للمشوار #{trip['trip_id']}</b>\n\n"
                    f"👤 الكابتن: {self.html(user.first_name)}\n\n"
                    f"📍 من: {self.html(trip['pickup'])}\n"
                    f"🏁 إلى: {self.html(trip['destination'])}"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📩 التواصل مع العميل", url=f"tg://user?id={trip['customer_id']}")]
                ])
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار الكابتن: {e}")

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

        await self.process_take_trip(context, user, trip, from_query=query)

    async def handle_customer_contact(self, update, context):
        query = update.callback_query
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return

        trip = self.db.get_trip(trip_id)
        if not trip:
            await query.answer("❌ الطلب غير موجود.", show_alert=True)
            return
        if query.from_user.id != trip["customer_id"]:
            await query.answer("❌ هذا الزر مخصص لصاحب الطلب.", show_alert=True)
            return

        drivers = self.db.get_ready_drivers(trip_id)
        if not drivers:
            await query.answer("⏳ لم يسجل أي كابتن جاهز حتى الآن.", show_alert=True)
            return

        buttons = [
            [InlineKeyboardButton(f"📩 التواصل مع {d['driver_name']}", url=f"tg://user?id={d['driver_id']}")]
            for d in drivers
        ]

        await query.answer()
        await query.message.reply_text("🚕 اختر الكابتن للتواصل:", reply_markup=InlineKeyboardMarkup(buttons))

    async def handle_close_trip(self, update, context):
        query = update.callback_query
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return

        trip = self.db.get_trip(trip_id)
        if not trip:
            await query.answer("❌ الطلب غير موجود.", show_alert=True)
            return
        if query.from_user.id != trip["customer_id"]:
            await query.answer("⚠️ صاحب الطلب فقط يستطيع الإغلاق.", show_alert=True)
            return
        if trip["status"] != "active":
            await query.answer("⚠️ المشوار مغلق مسبقاً.", show_alert=True)
            return

        self.db.close_trip(trip_id)
        await query.answer("✅ تم إغلاق المشوار.", show_alert=True)

        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(
                    f"✅ <b>تم إغلاق المشوار #{trip_id}</b>\n\n"
                    f"👤 العميل: {self.html(trip['customer_name'])}\n"
                    f"📍 من: {self.html(trip['pickup'])}\n"
                    f"🏁 إلى: {self.html(trip['destination'])}\n\n"
                    f"شكراً لاستخدامكم مشاوير جدة 🚘"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"خطأ في إشعار الإغلاق: {e}")

    async def handle_callback_buttons(self, update, context):
        query = update.callback_query
        data = query.data or ""
        user = query.from_user

        if data.startswith("btn_customer:") or data.startswith("btn_driver:"):
            role = "customer" if data.startswith("btn_customer:") else "driver"
            if user.id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر مخصص للإدارة فقط.", show_alert=True)
                return
            try:
                target_id = int(data.split(":")[1])
            except Exception:
                await query.answer("❌ حدث خطأ.", show_alert=True)
                return

            self.db.set_role(target_id, role)
            role_text = "عميل 👤" if role == "customer" else "كابتن 🚕"
            await query.answer(f"✅ تم تحديد العضو كـ {role_text}", show_alert=True)

            try:
                await query.message.edit_text(
                    f"✅ <b>تم تحديد الدور</b>\n\n"
                    f"👤 المستخدم: <code>{target_id}</code>\n"
                    f"🎯 الدور: {role_text}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            return

        if data == "btn_complaints":
            await query.answer()
            await query.message.reply_text(f"⚠️ للتواصل مع الإدارة:\n@{ADMIN_USERNAME}")

    async def handle_message(self, update, context):
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        if not message or not user or not chat:
            return
        if chat.id != GROUP_ID:
            return

        text = message.text or message.caption or ""
        if not text.strip():
            return

        logger.info(f"🔥 رسالة | CHAT={chat.id} | USER={user.id} | TEXT={text}")

        self.db.save_user(user)

        if self.db.is_banned(user.id):
            await self.delete_message(message)
            return

        # حماية
        if self.contains_phone_number(text):
            await self.issue_violation(update, context, "نشر رقم جوال داخل القروب ممنوع")
            return
        if self.contains_private_word(text):
            await self.issue_violation(update, context, "كتابة كلمة «خاص» داخل القروب ممنوعة")
            return
        if self.contains_unauthorized_link(text):
            await self.issue_violation(update, context, "نشر الروابط أو الإعلانات الخارجية ممنوع")
            return

        # إلغاء الطلب المعلق
        if user.id in self.pending_trips:
            if text.strip() in ["الغاء", "إلغاء", "كنسل", "إلغاء الطلب"]:
                del self.pending_trips[user.id]
                await message.reply_text("❌ تم إلغاء طلب المشوار المعلق.")
                return

        # التواجد
        presence_location = self.detect_presence(text)
        if presence_location is not None:
            if not presence_location.strip():
                await message.reply_text(
                    "📍 <b>وين موقع تواجدك؟</b>\n\n"
                    "مثال:\n«متواجد في الفضيلة»\nأو:\n«متواجد بالحرازات لأي مشوار»",
                    parse_mode=ParseMode.HTML
                )
                return
            await self.handle_presence(update, context, presence_location)
            return

        # الرد النصي "جاهز"
        if message.reply_to_message and "جاهز" in text.strip():
            replied_msg_id = message.reply_to_message.message_id
            trip = self.db.get_trip_by_message_id(replied_msg_id)
            if trip and trip["status"] == "active":
                await self.process_take_trip(context, user, trip)
                return

        # طلب معلق
        if user.id in self.pending_trips:
            pending = self.pending_trips[user.id]
            new_pickup, new_dest = self.extract_route(text)

            if not new_pickup or not new_dest:
                found = []
                normalized = self.normalize_text(text)
                for location in sorted(LOCATIONS, key=lambda x: len(self.normalize_text(x)), reverse=True):
                    normalized_location = self.normalize_text(location)
                    if normalized_location in normalized and location not in found:
                        found.append(location)

                if len(found) >= 2:
                    new_pickup, new_dest = found[0], found[1]
                elif len(found) == 1:
                    if not pending["pickup"]:
                        new_pickup = found[0]
                    elif not pending["destination"]:
                        new_dest = found[0]

            pickup = pending["pickup"] or new_pickup
            destination = pending["destination"] or new_dest

            if pickup and destination:
                del self.pending_trips[user.id]
                await self.handle_trip(update, context, pending["type"], pickup, destination)
                return

            self.pending_trips[user.id] = {
                "type": pending["type"], "pickup": pickup, "destination": destination,
            }

            if not pickup:
                await message.reply_text("📍 ما زال ناقص: من وين تنطلق؟")
            else:
                await message.reply_text("🏁 ما زال ناقص: إلى وين رايح؟")
            return

        # طلب مشوار جديد
        trip_type, pickup, destination = self.detect_trip(text)
        if trip_type:
            await self.handle_trip(update, context, trip_type, pickup, destination)
            return

        # التحية
        normalized = self.normalize_text(text).strip()
        for greeting in GREETINGS:
            if normalized == self.normalize_text(greeting):
                await message.reply_text(
                    "وعليكم السلام ورحمة الله وبركاته 🌹\n"
                    "حياك الله في مشاوير جدة 🚘"
                )
                return


# ============================================================
# 🌐 أوامر خارج الكلاس
# ============================================================

async def chat_id_command(update, context):
    chat = update.effective_chat
    if not chat:
        return
    if chat.type in ("group", "supergroup"):
        text = (
            f"📌 <b>بيانات القروب</b>\n\n"
            f"🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
            f"📋 النوع: <code>{chat.type}</code>\n"
            f"🏷 الاسم: {chat.title or 'بدون اسم'}"
        )
    else:
        text = (
            f"📌 <b>بيانات المحادثة</b>\n\n"
            f"🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
            f"📋 النوع: <code>{chat.type}</code>"
        )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def start_command(update, context):
    user = update.effective_user
    if not user:
        return
    bot_instance.db.save_user(user)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 أنا عميل", callback_data=f"btn_customer:{user.id}"),
            InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"btn_driver:{user.id}")
        ],
        [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")]
    ])
    await update.effective_message.reply_text(
        WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=keyboard
    )


async def mybots_command(update, context):
    user = update.effective_user
    await update.effective_message.reply_text(
        "🤖 <b>حالة البوت</b>\n\n"
        f"👤 المستخدم: {user.first_name}\n"
        f"🆔 معرفك: <code>{user.id}</code>\n"
        f"📌 معرف القروب: <code>{GROUP_ID}</code>\n"
        "✅ البوت يعمل.",
        parse_mode=ParseMode.HTML
    )


async def error_handler(update, context):
    logger.error("❌ حدث خطأ:", exc_info=context.error)


# ============================================================
# 🚀 التشغيل
# ============================================================

def main():
    global bot_instance

    if not TOKEN:
        raise RuntimeError("❌ لم يتم العثور على BOT_TOKEN")

    bot_instance = SmartRidesBot()

    application = (
        Application.builder().token(TOKEN).build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chatid", chat_id_command))
    application.add_handler(CommandHandler("mybots", mybots_command))

    application.add_handler(
        ChatMemberHandler(bot_instance.handle_chat_member, ChatMemberHandler.CHAT_MEMBER)
    )

    application.add_handler(
        CallbackQueryHandler(bot_instance.handle_take_trip, pattern=r"^take_trip:")
    )
    application.add_handler(
        CallbackQueryHandler(bot_instance.handle_customer_contact, pattern=r"^customer_contact:")
    )
    application.add_handler(
        CallbackQueryHandler(bot_instance.handle_close_trip, pattern=r"^close_trip:")
    )
    application.add_handler(
        CallbackQueryHandler(bot_instance.handle_callback_buttons, pattern=r"^btn_")
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message)
    )

    application.add_error_handler(error_handler)

    logger.info("=" * 60)
    logger.info("🚀 تشغيل بوت مشاوير جدة")
    logger.info(f"📌 GROUP_ID = {GROUP_ID}")
    logger.info(f"📌 ADMIN_IDS = {ADMIN_IDS}")
    logger.info("=" * 60)

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
