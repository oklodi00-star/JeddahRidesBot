"""
🤖 بوت مشاوير جدة الذكي

- العميل يرسل طلبه مباشرة بدون تسجيل مسبق
- الكابتن يضغط جاهز مباشرة بدون تسجيل مسبق
- زر التواصل يفتح الخاص مباشرة
- منع كلمة "خاص"
- منع أرقام الجوال
- منع الروابط الخارجية
- 3 مخالفات = كتم 24 ساعة
- تسجيل تواجد الكابتن مرة واحدة يومياً
- تكرار التواجد = مخالفة
- أمر /chatid لمعرفة آيدي القروب الحقيقي
- أمر /mybots لعرض حالة البوت
- ✅ يفهم السياق الكامل (التحية + الطلب في رسالة واحدة)
- ✅ يسأل عن المواقع الناقصة ويكمل الطلب
- ✅ ترحيب تلقائي بدون تكرار
- ✅ المشرف فقط يحدد دور العضو (عميل/كابتن)
- ✅ يفهم "إلين / لين / إلا / إلی" (لهجة سعودية)
- ✅ إشعار إغلاق المشوار في القروب
- ✅ إصلاح نظام التواجد
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


# ============================================================
# ⚠️ آيدي القروب والمشرف
# ============================================================

GROUP_ID = -1003716441020

GROUP_NAME = "🚘 مشاوير جدة وضواحيها"

ADMIN_USERNAME = "klodi500"

ADMIN_IDS = [
    952638746
]

ALLOWED_GROUP_LINK = "https://t.me/JeddahRidesGroup"

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

أو باللهجة السعودية:

«من الحرازات إلين تيسير»

🤖 سيقوم البوت بتسجيل الطلب وإنشاء بطاقة للمشوار.

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

«متواجد بالفيحاء لأي مشوار»

⚠️ يسمح بتسجيل التواجد مرة واحدة يومياً.

━━━━━━━━━━━━━━━━━━

🚫 <b>مهم:</b>

ممنوع كتابة «خاص».

ممنوع نشر أرقام الجوال.

ممنوع نشر الروابط الخارجية.

التواصل يكون عن طريق أزرار البوت فقط.
"""


# ============================================================
# 📚 الكلمات المفتاحية
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري",
    "شهريه",
    "شهرياً",
    "شهريا",
    "بالشهر",
    "دوام",
    "مدرسه",
    "مدرسة",
    "جامعه",
    "جامعة",
    "التزام",
    "اسبوعي",
    "أسبوعي",
    "يومي",
    "يوميا",
    "يومياً",
    "مشوار يومي",
    "توصيل يومي"
]


NORMAL_TRIP_WORDS = [
    "مشوار",
    "مشاوير",
    "توصيل",
    "توصيله",
    "توصيلة",
    "يوصلني",
    "يوديني",
    "ابغى مشوار",
    "ابي مشوار",
    "أبي مشوار",
    "ابغا مشوار",
    "أبغا مشوار",
    "احتاج توصيل",
    "أحتاج توصيل",
    "محتاج توصيل",
    "محتاجة توصيل",
    "من يوصلني",
    "اوصلني",
    "أوصلني",
    "ودني",
    "خذني",
    "ابي اروح",
    "أبي أروح",
    "ابغى اروح",
    "أبغى اروح",
    "ابغا اروح",
    "اريد مشوار"
]


# ============================================================
# 📍 كلمات التواجد
# ============================================================

PRESENCE_WORDS = [
    "متواجد",
    "متواجده",
    "متواجدة",
    "موجود",
    "موجوده",
    "موجودة",
    "متوفر",
    "متوفرة",
    "متوفره",
    "متاح",
    "متاحة",
    "متاحه",
    "انا في",
    "أنا في",
    "انا عند",
    "أنا عند",
    "واقف",
    "واقفه",
    "واقفة",
    "في الموقع",
    "بالخدمة",
    "بالخدمه"
]


# ============================================================
# 📍 المواقع
# ============================================================

LOCATIONS = [
    "الفضيلة",
    "الفضيله",

    "الرغامة",
    "الرغامه",

    "الخمرة",
    "الخمره",

    "الوزيرية",
    "الوزيريه",

    "السنابل",

    "التيسير",
    "تيسير",

    "الحرازات",
    "الحرازات الشمالية",
    "الحرازات الجنوبية",

    "النسيم",

    "الأندلس",
    "الاندلس",
    "الأندلس مول",
    "الاندلس مول",

    "الصناعية",

    "الزهراء",

    "النخيل",

    "الصالحية",

    "الروضة",

    "الصفا",

    "المروة",

    "الجامعة",

    "الحمراء",

    "الربوة",

    "النزهة",

    "المشرفة",

    "بني مالك",

    "الحمدانية",

    "المحمدية",

    "الخالدية",

    "النعيم",

    "السلامة",

    "الشاطئ",

    "أبحر",
    "ابحر",

    "التوفيق",

    "العدل",

    "المنار",

    "الواحة",

    "الفيصلية",

    "الريان",

    "الوادي",

    "الفلاح",

    "النهضة",

    "الرابية",

    "السلام",

    "المرجان",

    "الكورنيش",

    "الصالة",

    "الفيحاء",

    "مكة",
    "جدة"
]


# ============================================================
# 🔄 كلمات الاتجاه
# ============================================================

TO_WORDS_PATTERN = r"(?:الى|الي|إلى|إلين|لين|إلا|إلی|لل|ل|to)"


# ============================================================
# 👋 التحيات
# ============================================================

GREETINGS = [
    "السلام عليكم",
    "سلام عليكم",
    "السلام",
    "سلام",
    "صباح الخير",
    "مساء الخير",
    "هلا",
    "اهلا",
    "مرحبا"
]


# ============================================================
# 💾 قاعدة البيانات
# ============================================================

class Database:

    def __init__(self):
        self.conn = sqlite3.connect(
            DB_FILE,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.init_db()

    # --------------------------------------------------------
    # إنشاء الجداول
    # --------------------------------------------------------

    def init_db(self):

        cur = self.conn.cursor()

        # المستخدمين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                role TEXT DEFAULT '',
                registration_date TEXT
            )
        """)

        # المشاوير
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

        # الكباتن الجاهزين
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

        # المخالفات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                user_id INTEGER PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_reason TEXT,
                updated_at TEXT
            )
        """)

        # المحظورين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                created_at TEXT
            )
        """)

        # التواجد
        cur.execute("""
            CREATE TABLE IF NOT EXISTS presence (
                user_id INTEGER PRIMARY KEY,
                location TEXT,
                last_date TEXT,
                updated_at TEXT
            )
        """)

        self.conn.commit()

    # --------------------------------------------------------
    # حفظ المستخدم
    # --------------------------------------------------------

    def save_user(self, user):

        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO users
            (
                user_id,
                name,
                username,
                registration_date
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                username = excluded.username
        """, (
            user.id,
            user.full_name,
            user.username or "",
            datetime.now(SAUDI_TZ).isoformat()
        ))

        self.conn.commit()

    # --------------------------------------------------------
    # تحديد الدور
    # --------------------------------------------------------

    def set_role(self, user_id, role):

        cur = self.conn.cursor()

        cur.execute(
            "UPDATE users SET role = ? WHERE user_id = ?",
            (role, user_id)
        )

        self.conn.commit()

    # --------------------------------------------------------
    # معرفة الدور
    # --------------------------------------------------------

    def get_role(self, user_id):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT role FROM users WHERE user_id = ?",
            (user_id,)
        )

        row = cur.fetchone()

        return row["role"] if row else ""

    # --------------------------------------------------------
    # هل المستخدم محظور؟
    # --------------------------------------------------------

    def is_banned(self, user_id):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT 1 FROM banned_users WHERE user_id = ?",
            (user_id,)
        )

        return cur.fetchone() is not None

    # --------------------------------------------------------
    # إنشاء مشوار
    # --------------------------------------------------------

    def create_trip(
        self,
        message_id,
        customer_id,
        customer_name,
        pickup,
        destination,
        trip_type,
        original_text
    ):

        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO trips
            (
                message_id,
                customer_id,
                customer_name,
                pickup,
                destination,
                trip_type,
                original_text,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            customer_id,
            customer_name,
            pickup,
            destination,
            trip_type,
            original_text,
            datetime.now(SAUDI_TZ).isoformat()
        ))

        self.conn.commit()

        return cur.lastrowid

    # --------------------------------------------------------
    # جلب المشوار
    # --------------------------------------------------------

    def get_trip(self, trip_id):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT * FROM trips WHERE trip_id = ?",
            (trip_id,)
        )

        row = cur.fetchone()

        return dict(row) if row else None

    # --------------------------------------------------------
    # إغلاق المشوار
    # --------------------------------------------------------

    def close_trip(self, trip_id):

        cur = self.conn.cursor()

        cur.execute(
            "UPDATE trips SET status = 'closed' WHERE trip_id = ?",
            (trip_id,)
        )

        self.conn.commit()

    # --------------------------------------------------------
    # إضافة كابتن جاهز
    # --------------------------------------------------------

    def add_ready_driver(
        self,
        trip_id,
        driver_id,
        driver_name
    ):

        cur = self.conn.cursor()

        try:

            cur.execute("""
                INSERT INTO ready_drivers
                (
                    trip_id,
                    driver_id,
                    driver_name,
                    created_at
                )
                VALUES (?, ?, ?, ?)
            """, (
                trip_id,
                driver_id,
                driver_name,
                datetime.now(SAUDI_TZ).isoformat()
            ))

            self.conn.commit()

            return True

        except sqlite3.IntegrityError:

            return False

    # --------------------------------------------------------
    # جلب الكباتن الجاهزين
    # --------------------------------------------------------

    def get_ready_drivers(self, trip_id):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM ready_drivers
            WHERE trip_id = ?
            ORDER BY id ASC
        """, (trip_id,))

        return [
            dict(row)
            for row in cur.fetchall()
        ]

    # --------------------------------------------------------
    # عدد المخالفات
    # --------------------------------------------------------

    def get_violation_count(self, user_id):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT count FROM violations WHERE user_id = ?",
            (user_id,)
        )

        row = cur.fetchone()

        return row["count"] if row else 0

    # --------------------------------------------------------
    # إضافة مخالفة
    # --------------------------------------------------------

    def add_violation(self, user_id, reason):

        cur = self.conn.cursor()

        cur.execute(
            "SELECT count FROM violations WHERE user_id = ?",
            (user_id,)
        )

        row = cur.fetchone()

        if row:

            count = row["count"] + 1

            cur.execute("""
                UPDATE violations

                SET
                    count = ?,
                    last_reason = ?,
                    updated_at = ?

                WHERE user_id = ?
            """, (
                count,
                reason,
                datetime.now(SAUDI_TZ).isoformat(),
                user_id
            ))

        else:

            count = 1

            cur.execute("""
                INSERT INTO violations
                (
                    user_id,
                    count,
                    last_reason,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                count,
                reason,
                datetime.now(SAUDI_TZ).isoformat()
            ))

        self.conn.commit()

        return count

    # --------------------------------------------------------
    # تواجد اليوم
    # --------------------------------------------------------

    def get_presence_today(self, user_id):

        today = datetime.now(
            SAUDI_TZ
        ).date().isoformat()

        cur = self.conn.cursor()

        cur.execute("""
            SELECT *
            FROM presence
            WHERE user_id = ?
            AND last_date = ?
        """, (
            user_id,
            today
        ))

        row = cur.fetchone()

        return dict(row) if row else None

    # --------------------------------------------------------
    # حفظ التواجد
    # --------------------------------------------------------

    def save_presence(self, user_id, location):

        today = datetime.now(
            SAUDI_TZ
        ).date().isoformat()

        cur = self.conn.cursor()

        cur.execute("""
            INSERT INTO presence
            (
                user_id,
                location,
                last_date,
                updated_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET
                location = excluded.location,
                last_date = excluded.last_date,
                updated_at = excluded.updated_at
        """, (
            user_id,
            location,
            today,
            datetime.now(SAUDI_TZ).isoformat()
        ))

        self.conn.commit()


# ============================================================
# 🤖 البوت
# ============================================================

class SmartRidesBot:

    def __init__(self):

        self.db = Database()

        # الطلبات التي تنتظر معلومات ناقصة
        self.pending_trips = {}

        # حماية من تكرار الترحيب
        self.welcomed_members = set()

    # ========================================================
    # 🧹 أدوات مساعدة
    # ========================================================

    def normalize_text(self, text):

        if not text:
            return ""

        text = text.lower()

        replacements = {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ى": "ي",
            "ة": "ه",
            "ؤ": "و",
            "ئ": "ي"
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        text = re.sub(
            r"[\u064B-\u065F\u0670]",
            "",
            text
        )

        return text

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    def html(self, text):

        if not text:
            return ""

        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    # --------------------------------------------------------
    # إزالة التحيات
    # --------------------------------------------------------

    def strip_greetings(self, text):

        if not text:
            return ""

        cleaned = text

        for g in sorted(
            GREETINGS,
            key=len,
            reverse=True
        ):

            cleaned = re.sub(
                re.escape(g),
                " ",
                cleaned,
                flags=re.IGNORECASE
            )

        return re.sub(
            r"\s+",
            " ",
            cleaned
        ).strip()

    # --------------------------------------------------------
    # كشف رقم الجوال
    # --------------------------------------------------------

    def contains_phone_number(self, text):

        if not text:
            return False

        translation = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789"
        )

        text = text.translate(translation)

        compact = re.sub(
            r"[\s\-\(\)]",
            "",
            text
        )

        patterns = [
            r"(?<!\d)05\d{8}(?!\d)",
            r"(?<!\d)5\d{8}(?!\d)",
            r"(?<!\d)9665\d{8}(?!\d)",
            r"(?<!\d)\+9665\d{8}(?!\d)",
        ]

        return any(
            re.search(pattern, compact)
            for pattern in patterns
        )

    # --------------------------------------------------------
    # منع كلمة خاص
    # --------------------------------------------------------

    def contains_private_word(self, text):

        normalized = self.normalize_text(text)

        words = re.findall(
            r"[\w\u0600-\u06FF]+",
            normalized
        )

        forbidden = {
            "خاص",
            "بالخاص",
            "للخاص",
            "خاصني",
            "خاصك"
        }

        return any(
            word in forbidden
            for word in words
        )

    # --------------------------------------------------------
    # منع الروابط الخارجية
    # --------------------------------------------------------

    def contains_unauthorized_link(self, text):

        if not text:
            return False

        links = re.findall(
            r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
            text.lower()
        )

        for link in links:

            if ALLOWED_GROUP_LINK.lower() in link:
                continue

            return True

        return False

    # ========================================================
    # 🚗 استخراج المسار
    # ========================================================

    def extract_route(self, text):

        if not text:
            return None, None

        normalized = self.normalize_text(text)

        # ----------------------------------------------------
        # من X إلى Y
        # ----------------------------------------------------

        pattern1 = rf"من\s+(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)"

        match = re.search(
            pattern1,
            normalized,
            re.IGNORECASE
        )

        if match:

            pickup = re.sub(
                r"[.!،,؟?]+$",
                "",
                match.group(1).strip()
            ).strip()

            destination = re.sub(
                r"[.!،,؟?]+$",
                "",
                match.group(2).strip()
            ).strip()

            destination = re.sub(
                r"\s+(?:الساعه|الساعة|بعد|قبل)\s+.*$",
                "",
                destination
            ).strip()

            if pickup and destination:
                return pickup, destination

        # ----------------------------------------------------
        # X إلى Y بدون كلمة من
        # ----------------------------------------------------

        pattern2 = rf"^(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)"

        match = re.search(
            pattern2,
            normalized,
            re.IGNORECASE
        )

        if match:

            pickup = re.sub(
                r"[.!،,؟?]+$",
                "",
                match.group(1).strip()
            ).strip()

            destination = re.sub(
                r"[.!،,؟?]+$",
                "",
                match.group(2).strip()
            ).strip()

            if (
                pickup
                and destination
                and len(pickup) > 1
            ):
                return pickup, destination

        # ----------------------------------------------------
        # البحث عن مواقع معروفة
        # ----------------------------------------------------

        found = []

        for location in sorted(
            LOCATIONS,
            key=len,
            reverse=True
        ):

            normalized_location = self.normalize_text(
                location
            )

            if (
                normalized_location in normalized
                and location not in found
            ):
                found.append(location)

        if len(found) >= 2:

            return found[0], found[1]

        return None, None

    # ========================================================
    # 🚗 اكتشاف طلب مشوار
    # ========================================================

    def detect_trip(self, text):

        clean_text = self.strip_greetings(text)

        normalized = self.normalize_text(
            clean_text
        )

        pickup, destination = self.extract_route(
            clean_text
        )

        has_intent = any(
            self.normalize_text(word) in normalized
            for word in (
                NORMAL_TRIP_WORDS
                + MONTHLY_TRIP_WORDS
            )
        )

        has_route = (
            bool(pickup and destination)
            or
            bool(
                re.search(
                    rf"من\s+.+?\s+{TO_WORDS_PATTERN}\s+.+",
                    normalized,
                    re.IGNORECASE
                )
            )
        )

        if not has_intent and not has_route:
            return None, None, None

        monthly = any(
            self.normalize_text(word) in normalized
            for word in MONTHLY_TRIP_WORDS
        )

        trip_type = (
            "monthly"
            if monthly
            else "normal"
        )

        return (
            trip_type,
            pickup,
            destination
        )

    # ========================================================
    # 📍 اكتشاف التواجد — النسخة المصححة
    # ========================================================

    def detect_presence(self, text):

        if not text:
            return None

        clean_text = self.strip_greetings(text)

        normalized = self.normalize_text(
            clean_text
        )

        # ----------------------------------------------------
        # هل الرسالة تحتوي على كلمة تواجد؟
        # ----------------------------------------------------

        has_presence = any(
            self.normalize_text(word) in normalized
            for word in PRESENCE_WORDS
        )

        if not has_presence:
            return None

        # ----------------------------------------------------
        # البحث عن المواقع المعروفة أولاً
        #
        # نرتب الأطول أولاً حتى:
        #
        # الحرازات الشمالية
        #
        # يتم التقاطها قبل:
        #
        # الحرازات
        # ----------------------------------------------------

        for location in sorted(
            LOCATIONS,
            key=len,
            reverse=True
        ):

            normalized_location = self.normalize_text(
                location
            )

            if normalized_location in normalized:

                return location

        # ----------------------------------------------------
        # البحث عن الموقع بعد:
        #
        # في
        # ب
        # عند
        # ----------------------------------------------------

        patterns = [
            r"(?:في|عند)\s+([^\s،,.!?؟]+)",
            r"\bب([^\s،,.!?؟]+)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                normalized
            )

            if match:

                location = match.group(1).strip()

                # تنظيف
                location = re.sub(
                    r"(لأي|لاي|اي|مشوار|مشاوير).*$",
                    "",
                    location
                ).strip()

                if location:
                    return location

        # ----------------------------------------------------
        # مثال:
        #
        # متواجد الفيحاء
        #
        # إذا لم تكن الفيحاء في قائمة المواقع
        # ----------------------------------------------------

        location_text = normalized

        remove_phrases = [
            "متواجد",
            "متواجده",
            "متواجدة",
            "موجود",
            "موجوده",
            "موجودة",
            "متوفر",
            "متوفره",
            "متوفرة",
            "متاح",
            "متاحه",
            "متاحة",
            "انا",
            "في",
            "عند",
            "بالخدمه",
            "بالخدمة",
            "لأي مشوار",
            "لاي مشوار",
            "لأي مشاوير",
            "لاي مشاوير",
            "للمشاوير",
            "للمشوار"
        ]

        for phrase in sorted(
            remove_phrases,
            key=len,
            reverse=True
        ):

            location_text = location_text.replace(
                self.normalize_text(phrase),
                " "
            )

        location_text = re.sub(
            r"\s+",
            " ",
            location_text
        ).strip()

        words = location_text.split()

        if words:

            return words[0]

        # ----------------------------------------------------
        # تواجد بدون موقع
        # ----------------------------------------------------

        return ""

    # ========================================================
    # 🗑️ حذف الرسالة
    # ========================================================

    async def delete_message(self, message):

        try:

            await message.delete()

        except Exception as e:

            logger.warning(
                f"تعذر حذف الرسالة: {e}"
            )

    # --------------------------------------------------------
    # حذف الرسالة بعد مدة
    # --------------------------------------------------------

    async def delete_later(self, context):

        try:

            await context.job.data.delete()

        except Exception:
            pass

    # ========================================================
    # ⚠️ المخالفات
    # ========================================================

    async def issue_violation(
        self,
        update,
        context,
        reason
    ):

        message = update.effective_message

        user = update.effective_user

        if not message or not user:
            return

        count = self.db.add_violation(
            user.id,
            reason
        )

        await self.delete_message(
            message
        )

        # ----------------------------------------------------
        # المخالفة الأولى
        # ----------------------------------------------------

        if count == 1:

            text = (
                f"⚠️ <b>تنبيه</b>\n\n"
                f"يا {self.html(user.first_name)}، "
                f"تم تسجيل المخالفة الأولى.\n"
                f"السبب: {reason}"
            )

        # ----------------------------------------------------
        # المخالفة الثانية
        # ----------------------------------------------------

        elif count == 2:

            text = (
                f"⚠️ <b>تحذير أخير</b>\n\n"
                f"يا {self.html(user.first_name)}، "
                f"تم تسجيل المخالفة الثانية.\n\n"
                f"⚠️ الثالثة = كتم 24 ساعة."
            )

        # ----------------------------------------------------
        # الثالثة
        # ----------------------------------------------------

        else:

            text = (
                f"🚫 <b>تم كتمك لمدة 24 ساعة</b>\n\n"
                f"السبب: {reason}"
            )

        try:

            warning = await context.bot.send_message(
                chat_id=message.chat_id,
                text=text,
                parse_mode=ParseMode.HTML
            )

            if context.job_queue:

                context.job_queue.run_once(
                    self.delete_later,
                    8,
                    data=warning
                )

        except Exception as e:

            logger.error(
                f"خطأ في إرسال التحذير: {e}"
            )

        # ----------------------------------------------------
        # كتم 24 ساعة
        # ----------------------------------------------------

        if count >= 3:

            try:

                until_date = (
                    datetime.now(SAUDI_TZ)
                    + timedelta(hours=24)
                )

                await context.bot.restrict_chat_member(
                    chat_id=message.chat_id,
                    user_id=user.id,
                    permissions=ChatPermissions(
                        can_send_messages=False
                    ),
                    until_date=until_date
                )

            except Exception as e:

                logger.error(
                    f"خطأ في كتم العضو: {e}"
                )

    # ========================================================
    # 👋 ترحيب الأعضاء الجدد
    # ========================================================

    async def _send_welcome(
        self,
        context,
        member
    ):

        # حماية من التكرار
        if member.id in self.welcomed_members:

            logger.info(
                f"⚠️ العضو {member.id} "
                f"تم ترحيبه مسبقاً — تجاهل"
            )

            return

        self.welcomed_members.add(
            member.id
        )

        logger.info(
            f"✅ إرسال ترحيب للعضو: "
            f"{member.id} - {member.first_name}"
        )

        # حفظ المستخدم
        try:

            self.db.save_user(
                member
            )

        except Exception as e:

            logger.error(
                f"⚠️ فشل حفظ المستخدم: {e}"
            )

        # ----------------------------------------------------
        # أزرار الترحيب
        # ----------------------------------------------------

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"👤 {member.first_name} عميل",
                    callback_data=f"btn_customer:{member.id}"
                ),

                InlineKeyboardButton(
                    f"🚕 {member.first_name} كابتن",
                    callback_data=f"btn_driver:{member.id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "⚠️ الشكاوي",
                    callback_data="btn_complaints"
                )
            ]
        ])

        try:

            sent = await context.bot.send_message(
                chat_id=GROUP_ID,

                text=(
                    WELCOME_TEXT
                    + "\n\n"
                    + f"👋 انضم: "
                    + f"<b>{self.html(member.first_name)}</b>"
                ),

                parse_mode=ParseMode.HTML,

                reply_markup=keyboard
            )

            logger.info(
                f"✅ تم إرسال الترحيب | "
                f"msg_id={sent.message_id}"
            )

        except Exception as e:

            logger.error(
                f"❌ فشل إرسال الترحيب: {e}",
                exc_info=True
            )

    # ========================================================
    # 👋 استقبال دخول الأعضاء
    # ========================================================

    async def handle_chat_member(
        self,
        update,
        context
    ):

        cm = update.chat_member

        if not cm:
            return

        logger.info(
            f"👋 CHAT_MEMBER | "
            f"CHAT={cm.chat.id} | "
            f"OLD={cm.old_chat_member.status} | "
            f"NEW={cm.new_chat_member.status}"
        )

        if cm.chat.id != GROUP_ID:
            return

        old_status = (
            cm.old_chat_member.status
        )

        new_status = (
            cm.new_chat_member.status
        )

        if (
            old_status in ("left", "kicked")
            and
            new_status in ("member", "restricted")
        ):

            user = cm.new_chat_member.user

            if user.is_bot:
                return

            await self._send_welcome(
                context,
                user
            )

    # ========================================================
    # 📍 تسجيل التواجد
    # ========================================================

    async def handle_presence(
        self,
        update,
        context,
        location
    ):

        message = update.effective_message

        user = update.effective_user

        if not message or not user:
            return

        # حفظ بيانات المستخدم فقط
        # لا نغير دوره تلقائياً
        self.db.save_user(user)

        # ----------------------------------------------------
        # التواجد مكرر؟
        # ----------------------------------------------------

        if self.db.get_presence_today(
            user.id
        ):

            await self.issue_violation(
                update,
                context,
                "تكرار إعلان التواجد أكثر من مرة في اليوم"
            )

            return

        # ----------------------------------------------------
        # حفظ التواجد
        # ----------------------------------------------------

        self.db.save_presence(
            user.id,
            location
        )

        # ----------------------------------------------------
        # الرد
        # ----------------------------------------------------

        await message.reply_text(
            f"📍 <b>تم تسجيل تواجدك</b>\n\n"
            f"🚕 الكابتن: "
            f"{self.html(user.first_name)}\n"
            f"📍 الموقع: "
            f"{self.html(location)}",
            parse_mode=ParseMode.HTML
        )

    # ========================================================
    # 🚗 تسجيل مشوار جديد
    # ========================================================

    async def handle_trip(
        self,
        update,
        context,
        trip_type,
        pickup,
        destination
    ):

        message = update.effective_message

        user = update.effective_user

        if not message or not user:
            return

        self.db.save_user(user)

        # ----------------------------------------------------
        # ملاحظة:
        # يبقى تعيين العميل هنا كما كان في الكود الأصلي
        # ----------------------------------------------------

        self.db.set_role(
            user.id,
            "customer"
        )

        # ----------------------------------------------------
        # معلومات ناقصة
        # ----------------------------------------------------

        if not pickup or not destination:

            self.pending_trips[user.id] = {
                "type": trip_type,
                "pickup": pickup,
                "destination": destination,
            }

            # لا يوجد أي موقع
            if not pickup and not destination:

                question = (
                    "📍 <b>من وين إلى وين؟</b>\n\n"
                    "مثال:\n"
                    "«من الحرازات إلين تيسير»"
                )

            # الانطلاق ناقص
            elif not pickup:

                question = (
                    f"📍 <b>ما زال ناقص: من وين تنطلق؟</b>\n\n"
                    f"🎯 الوصول: "
                    f"{self.html(destination)}"
                )

            # الوصول ناقص
            else:

                question = (
                    f"🏁 <b>ما زال ناقص: إلى وين رايح؟</b>\n\n"
                    f"📍 الانطلاق: "
                    f"{self.html(pickup)}"
                )

            await message.reply_text(
                question,
                parse_mode=ParseMode.HTML
            )

            return

        # ----------------------------------------------------
        # إنشاء المشوار
        # ----------------------------------------------------

        trip_id = self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            customer_name=(
                user.first_name
                or "العميل"
            ),
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            original_text=(
                message.text
                or ""
            )
        )

        # ----------------------------------------------------
        # أزرار المشوار
        # ----------------------------------------------------

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🚕 جاهز",
                    callback_data=f"take_trip:{trip_id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "📩 التواصل مع الكابتن",
                    callback_data=f"customer_contact:{trip_id}"
                )
            ],

            [
                InlineKeyboardButton(
                    "✅ تم المشوار",
                    callback_data=f"close_trip:{trip_id}"
                )
            ]
        ])

        type_badge = (
            "🔄 شهري"
            if trip_type == "monthly"
            else
            "🚗 عادي"
        )

        await message.reply_text(
            f"✅ <b>تم تسجيل طلبك</b>\n\n"
            f"📋 النوع: {type_badge}\n"
            f"📍 من: {self.html(pickup)}\n"
            f"🏁 إلى: {self.html(destination)}",

            parse_mode=ParseMode.HTML,

            reply_markup=keyboard
        )

    # ========================================================
    # 🚕 الكابتن يضغط جاهز
    # ========================================================

    async def handle_take_trip(
        self,
        update,
        context
    ):

        query = update.callback_query

        user = query.from_user

        try:

            trip_id = int(
                query.data.split(":")[1]
            )

        except Exception:

            await query.answer(
                "❌ حدث خطأ.",
                show_alert=True
            )

            return

        trip = self.db.get_trip(
            trip_id
        )

        if (
            not trip
            or trip["status"] != "active"
        ):

            await query.answer(
                "❌ المشوار غير متاح.",
                show_alert=True
            )

            return

        # العميل لا يأخذ مشواره
        if user.id == trip["customer_id"]:

            await query.answer(
                "😂 لا يمكنك أخذ مشوارك بنفسك.",
                show_alert=True
            )

            return

        self.db.save_user(user)

        # تسجيله ككابتن لأنه ضغط جاهز
        self.db.set_role(
            user.id,
            "driver"
        )

        if not self.db.add_ready_driver(
            trip_id,
            user.id,
            user.first_name or "الكابتن"
        ):

            await query.answer(
                "⚠️ أنت مسجل بالفعل لهذا المشوار.",
                show_alert=True
            )

            return

        await query.answer(
            "✅ تم تسجيل جاهزيتك.",
            show_alert=True
        )

        # ----------------------------------------------------
        # إشعار القروب
        # ----------------------------------------------------

        try:

            await context.bot.send_message(
                chat_id=GROUP_ID,

                text=(
                    f"🚕 <b>تم تسجيل كابتن "
                    f"للمشوار #{trip_id}</b>\n\n"
                    f"👤 الكابتن: "
                    f"{self.html(user.first_name)}\n\n"
                    f"📍 من: "
                    f"{self.html(trip['pickup'])}\n"
                    f"🏁 إلى: "
                    f"{self.html(trip['destination'])}"
                ),

                parse_mode=ParseMode.HTML,

                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "📩 التواصل مع العميل",
                            url=(
                                f"tg://user?id="
                                f"{trip['customer_id']}"
                            )
                        )
                    ]
                ])
            )

        except Exception as e:

            logger.error(
                f"خطأ في إرسال زر التواصل: {e}"
            )

    # ========================================================
    # 📩 تواصل العميل مع الكابتن
    # ========================================================

    async def handle_customer_contact(
        self,
        update,
        context
    ):

        query = update.callback_query

        try:

            trip_id = int(
                query.data.split(":")[1]
            )

        except Exception:

            await query.answer(
                "❌ حدث خطأ.",
                show_alert=True
            )

            return

        trip = self.db.get_trip(
            trip_id
        )

        if not trip:

            await query.answer(
                "❌ الطلب غير موجود.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # الزر للعميل صاحب الطلب فقط
        # ----------------------------------------------------

        if (
            query.from_user.id
            != trip["customer_id"]
        ):

            await query.answer(
                "❌ هذا الزر مخصص للعميل صاحب الطلب.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # الكباتن الجاهزين
        # ----------------------------------------------------

        drivers = self.db.get_ready_drivers(
            trip_id
        )

        if not drivers:

            await query.answer(
                "⏳ لم يسجل أي كابتن جاهز حتى الآن.",
                show_alert=True
            )

            return

        buttons = []

        for driver in drivers:

            buttons.append([
                InlineKeyboardButton(
                    f"📩 التواصل مع "
                    f"{driver['driver_name']}",

                    url=(
                        f"tg://user?id="
                        f"{driver['driver_id']}"
                    )
                )
            ])

        await query.answer()

        await query.message.reply_text(
            "🚕 اختر الكابتن للتواصل:",

            reply_markup=InlineKeyboardMarkup(
                buttons
            )
        )

    # ========================================================
    # ✅ إغلاق المشوار
    # ========================================================

    async def handle_close_trip(
        self,
        update,
        context
    ):

        query = update.callback_query

        try:

            trip_id = int(
                query.data.split(":")[1]
            )

        except Exception:

            await query.answer(
                "❌ حدث خطأ.",
                show_alert=True
            )

            return

        trip = self.db.get_trip(
            trip_id
        )

        if not trip:

            await query.answer(
                "❌ الطلب غير موجود.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # صاحب الطلب فقط
        # ----------------------------------------------------

        if (
            query.from_user.id
            != trip["customer_id"]
        ):

            await query.answer(
                "⚠️ صاحب الطلب فقط يستطيع الإغلاق.",
                show_alert=True
            )

            return

        if trip["status"] != "active":

            await query.answer(
                "⚠️ المشوار مغلق مسبقاً.",
                show_alert=True
            )

            return

        # ----------------------------------------------------
        # إغلاق
        # ----------------------------------------------------

        self.db.close_trip(
            trip_id
        )

        await query.answer(
            "✅ تم إغلاق المشوار.",
            show_alert=True
        )

        # ----------------------------------------------------
        # إزالة الأزرار من البطاقة
        # ----------------------------------------------------

        try:

            await query.message.edit_reply_markup(
                reply_markup=None
            )

        except Exception as e:

            logger.warning(
                f"تعذر إزالة الأزرار: {e}"
            )

        # ----------------------------------------------------
        # إشعار القروب
        # ----------------------------------------------------

        try:

            await context.bot.send_message(
                chat_id=GROUP_ID,

                text=(
                    f"✅ <b>تم إغلاق "
                    f"المشوار #{trip_id}</b>\n\n"
                    f"👤 العميل: "
                    f"{self.html(trip['customer_name'])}\n"
                    f"📍 من: "
                    f"{self.html(trip['pickup'])}\n"
                    f"🏁 إلى: "
                    f"{self.html(trip['destination'])}\n\n"
                    f"شكراً لاستخدامكم "
                    f"مشاوير جدة 🚘"
                ),

                parse_mode=ParseMode.HTML
            )

        except Exception as e:

            logger.error(
                f"خطأ في إرسال إشعار الإغلاق: {e}"
            )

    # ========================================================
    # 🎛️ الأزرار العامة
    # ========================================================

    async def handle_callback_buttons(
        self,
        update,
        context
    ):

        query = update.callback_query

        data = query.data or ""

        user = query.from_user

        # ----------------------------------------------------
        # تحديد عميل / كابتن
        # ----------------------------------------------------

        if (
            data.startswith("btn_customer:")
            or
            data.startswith("btn_driver:")
        ):

            role = (
                "customer"
                if data.startswith("btn_customer:")
                else
                "driver"
            )

            # الإدارة فقط
            if user.id not in ADMIN_IDS:

                await query.answer(
                    "❌ هذا الزر مخصص للإدارة فقط.",
                    show_alert=True
                )

                return

            try:

                target_id = int(
                    data.split(":")[1]
                )

            except Exception:

                await query.answer(
                    "❌ حدث خطأ.",
                    show_alert=True
                )

                return

            try:

                self.db.set_role(
                    target_id,
                    role
                )

            except Exception as e:

                logger.error(
                    f"خطأ في تحديث الدور: {e}"
                )

                await query.answer(
                    "❌ فشل التحديث.",
                    show_alert=True
                )

                return

            role_text = (
                "عميل 👤"
                if role == "customer"
                else
                "كابتن 🚕"
            )

            await query.answer(
                f"✅ تم تحديد العضو كـ {role_text}",
                show_alert=True
            )

            try:

                await query.message.edit_text(
                    f"✅ <b>تم تحديد الدور</b>\n\n"
                    f"👤 المستخدم: "
                    f"<code>{target_id}</code>\n"
                    f"🎯 الدور: {role_text}",

                    parse_mode=ParseMode.HTML
                )

            except Exception as e:

                logger.warning(
                    f"تعذر تعديل الرسالة: {e}"
                )

            return

        # ----------------------------------------------------
        # الشكاوي
        # ----------------------------------------------------

        if data == "btn_complaints":

            await query.answer()

            await query.message.reply_text(
                f"⚠️ للتواصل مع الإدارة:\n"
                f"@{ADMIN_USERNAME}"
            )


# ============================================================
# 📌 /chatid
# ============================================================

async def chat_id_command(
    update,
    context
):

    chat = update.effective_chat

    if not chat:
        return

    logger.info(
        f"🔎 CHATID | "
        f"ID={chat.id} | "
        f"TYPE={chat.type} | "
        f"TITLE={chat.title}"
    )

    if chat.type in [
        "group",
        "supergroup"
    ]:

        text = (
            "📌 <b>بيانات القروب</b>\n\n"
            f"🆔 Chat ID:\n"
            f"<code>{chat.id}</code>\n\n"
            f"📋 النوع: "
            f"<code>{chat.type}</code>\n"
            f"🏷 الاسم: "
            f"{chat.title or 'بدون اسم'}\n\n"
            "✅ أرسل لي هذا الرقم "
            "لأضعه لك في الكود."
        )

    else:

        text = (
            "📌 <b>بيانات المحادثة</b>\n\n"
            f"🆔 Chat ID:\n"
            f"<code>{chat.id}</code>\n\n"
            f"📋 النوع: "
            f"<code>{chat.type}</code>"
        )

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# /start
# ============================================================

async def start_command(
    update,
    context
):

    user = update.effective_user

    if user:

        bot_instance.db.save_user(
            user
        )

    if not update.message:
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👤 أنا عميل",
                callback_data=f"btn_customer:{user.id}"
            ),

            InlineKeyboardButton(
                "🚕 أنا كابتن",
                callback_data=f"btn_driver:{user.id}"
            )
        ],

        [
            InlineKeyboardButton(
                "⚠️ الشكاوي",
                callback_data="btn_complaints"
            )
        ]
    ])

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


# ============================================================
# /mybots
# ============================================================

async def mybots_command(
    update,
    context
):

    user = update.effective_user

    text = (
        "🤖 <b>حالة البوت</b>\n\n"
        f"👤 المستخدم: "
        f"{user.first_name}\n"
        f"🆔 معرفك: "
        f"<code>{user.id}</code>\n"
        f"📌 معرف القروب الحالي: "
        f"<code>{GROUP_ID}</code>\n"
        "✅ البوت يعمل بشكل طبيعي."
    )

    await update.effective_message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )


# ============================================================
# ❌ معالجة الأخطاء
# ============================================================

async def error_handler(
    update,
    context
):

    logger.error(
        "❌ حدث خطأ أثناء معالجة Update:",
        exc_info=context.error
    )


# ============================================================
# 📩 استقبال رسائل القروب
# ============================================================

async def handle_message(
    update,
    context
):

    message = update.effective_message

    user = update.effective_user

    chat = update.effective_chat

    if not message or not user or not chat:
        return

    logger.info(
        f"🔥 وصلت رسالة | "
        f"CHAT_ID={chat.id} | "
        f"TYPE={chat.type} | "
        f"TITLE={chat.title} | "
        f"USER={user.id} | "
        f"TEXT={message.text or message.caption or ''}"
    )

    # --------------------------------------------------------
    # التأكد من القروب
    # --------------------------------------------------------

    if chat.id != GROUP_ID:

        logger.warning(
            f"⚠️ رسالة من قروب غير معتمد: "
            f"{chat.id}"
        )

        return

    text = (
        message.text
        or message.caption
        or ""
    )

    if not text.strip():
        return

    # --------------------------------------------------------
    # حفظ المستخدم
    # --------------------------------------------------------

    bot_instance.db.save_user(
        user
    )

    # --------------------------------------------------------
    # المحظور
    # --------------------------------------------------------

    if bot_instance.db.is_banned(
        user.id
    ):
        return

    # ========================================================
    # 🚫 الحماية والمخالفات
    # ========================================================

    # رقم جوال
    if bot_instance.contains_phone_number(
        text
    ):

        await bot_instance.issue_violation(
            update,
            context,
            "نشر رقم جوال داخل القروب ممنوع"
        )

        return

    # كلمة خاص
    if bot_instance.contains_private_word(
        text
    ):

        await bot_instance.issue_violation(
            update,
            context,
            "كتابة كلمة «خاص» داخل القروب ممنوعة"
        )

        return

    # روابط
    if bot_instance.contains_unauthorized_link(
        text
    ):

        await bot_instance.issue_violation(
            update,
            context,
            "نشر الروابط أو الإعلانات الخارجية ممنوع"
        )

        return

    # ========================================================
    # 📍 التواجد — يجب أن يكون قبل أي طلب مشوار
    # ========================================================
    #
    # هذه أهم نقطة في الإصلاح.
    #
    # أي رسالة فيها:
    #
    # متواجد
    # موجود
    # متوفر
    # أنا في
    # أنا عند
    #
    # يتم التعامل معها كتواجد أولاً.
    #
    # مثال:
    #
    # متواجد بالفيحاء لأي مشوار
    #
    # لن تصل أبداً إلى detect_trip().
    #
    # ========================================================

    presence_location = (
        bot_instance.detect_presence(text)
    )

    if presence_location is not None:

        # ----------------------------------------------------
        # تواجد بدون موقع
        # ----------------------------------------------------

        if not presence_location.strip():

            await message.reply_text(
                "📍 <b>وين موقع تواجدك؟</b>\n\n"
                "مثال:\n"
                "«متواجد في الفيحاء»\n"
                "أو\n"
                "«متواجد بالحرازات لأي مشوار»",

                parse_mode=ParseMode.HTML
            )

            return

        # ----------------------------------------------------
        # تسجيل التواجد
        # ----------------------------------------------------

        await bot_instance.handle_presence(
            update,
            context,
            presence_location
        )

        return

    # ========================================================
    # 🚗 الطلبات المعلقة
    # ========================================================

    if user.id in bot_instance.pending_trips:

        pending = (
            bot_instance.pending_trips[user.id]
        )

        new_pickup, new_dest = (
            bot_instance.extract_route(text)
        )

        if not new_pickup or not new_dest:

            found = []

            normalized = (
                bot_instance.normalize_text(text)
            )

            for loc in sorted(
                LOCATIONS,
                key=len,
                reverse=True
            ):

                normalized_loc = (
                    bot_instance.normalize_text(loc)
                )

                if (
                    normalized_loc in normalized
                    and loc not in found
                ):

                    found.append(loc)

            if len(found) >= 2:

                new_pickup = found[0]

                new_dest = found[1]

            elif len(found) == 1:

                if not pending["pickup"]:

                    new_pickup = found[0]

                elif not pending["destination"]:

                    new_dest = found[0]

        pickup = (
            pending["pickup"]
            or new_pickup
        )

        destination = (
            pending["destination"]
            or new_dest
        )

        # ----------------------------------------------------
        # اكتمل الطلب
        # ----------------------------------------------------

        if pickup and destination:

            del bot_instance.pending_trips[
                user.id
            ]

            await bot_instance.handle_trip(
                update,
                context,
                pending["type"],
                pickup,
                destination
            )

            return

        # ----------------------------------------------------
        # ما زالت معلومات ناقصة
        # ----------------------------------------------------

        bot_instance.pending_trips[
            user.id
        ] = {
            "type": pending["type"],
            "pickup": pickup,
            "destination": destination,
        }

        if not pickup:

            await message.reply_text(
                "📍 ما زال ناقص: من وين تنطلق؟"
            )

        else:

            await message.reply_text(
                "🏁 ما زال ناقص: إلى وين رايح؟"
            )

        return

    # ========================================================
    # 🚗 تحليل طلب مشوار جديد
    # ========================================================

    trip_type, pickup, destination = (
        bot_instance.detect_trip(text)
    )

    if trip_type:

        await bot_instance.handle_trip(
            update,
            context,
            trip_type,
            pickup,
            destination
        )

        return

    # ========================================================
    # 👋 التحية فقط
    # ========================================================

    normalized = (
        bot_instance.normalize_text(text)
        .strip()
    )

    for greeting in GREETINGS:

        if (
            normalized
            ==
            bot_instance.normalize_text(
                greeting
            )
        ):

            await message.reply_text(
                "وعليكم السلام ورحمة الله وبركاته 🌹\n"
                "حياك الله في مشاوير جدة 🚘"
            )

            return


# ============================================================
# 🚀 التشغيل
# ============================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "❌ لم يتم العثور على BOT_TOKEN "
            "في متغيرات البيئة."
        )

    global bot_instance

    bot_instance = SmartRidesBot()

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # ========================================================
    # 📌 الأوامر
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    application.add_handler(
        CommandHandler(
            "chatid",
            chat_id_command
        )
    )

    application.add_handler(
        CommandHandler(
            "mybots",
            mybots_command
        )
    )

    # ========================================================
    # 👋 ترحيب الأعضاء
    # ========================================================

    application.add_handler(
        ChatMemberHandler(
            bot_instance.handle_chat_member,
            ChatMemberHandler.CHAT_MEMBER
        )
    )

    # ========================================================
    # 🎛️ الأزرار
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            bot_instance.handle_take_trip,
            pattern=r"^take_trip:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            bot_instance.handle_customer_contact,
            pattern=r"^customer_contact:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            bot_instance.handle_close_trip,
            pattern=r"^close_trip:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            bot_instance.handle_callback_buttons,
            pattern=r"^btn_"
        )
    )

    # ========================================================
    # 📩 الرسائل العادية
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    # ========================================================
    # ❌ الأخطاء
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    # ========================================================
    # 🚀 التشغيل
    # ========================================================

    logger.info("=" * 50)

    logger.info(
        "🚀 تشغيل بوت مشاوير جدة..."
    )

    logger.info(
        f"📌 GROUP_ID الحالي = {GROUP_ID}"
    )

    logger.info(
        f"📌 ADMIN_IDS = {ADMIN_IDS}"
    )

    logger.info("=" * 50)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )


# ============================================================
# ▶️ البداية
# ============================================================

if __name__ == "__main__":
    main()
