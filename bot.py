"""
🤖 بوت مشاوير جدة - النسخة النهائية الشاملة (محدثة)
- دمج جميع أحياء جدة (أكثر من 300 حي ومنطقة).
- إضافة نظام مكافحة الإزعاج (5 رسائل في 10 ثواني = كتم).
- إضافة زر "إلغاء الكتم" للمشرفين.
- الحفاظ على جميع الميزات السابقة والإصلاحات.
"""

import os
import re
import logging
import sqlite3
import time

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ContextTypes, filters,
)

# ============================================================
# ⚙️ الإعدادات
# ============================================================
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROUP_ID = -1003716441020
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
ADMIN_USERNAME = "klodi500"
ADMIN_IDS = [952638746]
ALLOWED_GROUP_LINK = "t.me/JeddahRidesGroup"
SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

# إعدادات مكافحة الإزعاج
SPAM_TIME_WINDOW = 10  # بالثواني
SPAM_MESSAGE_LIMIT = 5  # عدد الرسائل المسموح بها في النافذة الزمنية

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
أو: «من الحرازات إلين تيسير»
🤖 سيقوم البوت بتسجيل الطلب.
━━━━━━━━━━━━━━━━━━
🚕 <b>طريقة الكابتن:</b>
اضغط زر «🚕 جاهز» أو اقتبس الطلب واكتب «جاهز».
━━━━━━━━━━━━━━━━━━
📍 <b>إعلان التواجد:</b>
«متواجد في الفضيلة» أو «متواجد بالحرازات لأي مشوار»
⚠️ يسمح بتسجيل التواجد مرة واحدة يومياً.
━━━━━━━━━━━━━━━━━━
🚫 <b>مهم:</b>
ممنوع «خاص» / أرقام الجوال / الروابط الخارجية.
ممنوع الإزعاج وتكرار الرسائل.
"""

# ============================================================
# 📚 الكلمات والقوائم
# ============================================================
MONTHLY_TRIP_WORDS = [
    "شهري", "شهرية", "شهريه", "شهريا", "بالشهر", "دوام", "مدرسه",
    "مدرسة", "جامعه", "جامعة", "التزام", "اسبوعي", "أسبوعي",
    "يومي", "يوميا", "مشوار يومي", "توصيل يومي",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "مشاوير", "توصيل", "توصيله", "يوصلني",
    "يوديني", "ابغى مشوار", "ابي مشوار", "ابغا مشوار",
    "احتاج توصيل", "محتاج توصيل", "من يوصلني", "اوصلني",
    "ودني", "خذني", "ابي اروح", "ابغى اروح", "ابغا اروح",
]

PRESENCE_QUESTION_WORDS = [
    "مين", "وين", "احد", "الموجودين", "موجودين", "المتواجدين",
    "الموجود", "موجود",
]

# القائمة الشاملة لأحياء جدة (أكثر من 300 حي ومنطقة فرعية)
LOCATIONS_SET = {
    # ====================== شمال جدة (الشمالية) ======================
    "الاصالة", "ابحر الشمالية", "ابحر الجنوبية", "الفردوس", "الشراع", "الامواج",
    "الصواري", "الياقوت", "اللؤلؤ", "مطار الملك عبدالعزيز", "الزمرد", "المنارات",
    "الفنار", "البحيرات", "النور", "المروج", "الخليج", "النجمة", "الزهور",
    "الغربية", "الشويضي", "الغدير", "الربيع", "العقيق", "العبير", "الدرة",
    "طابة", "المجامع", "المزيرعة", "الفرقان", "اليسر", "الجزيرة", "الكورنيش",
    "المعرفة", "الودية", "الشاطئ", "الحمراء", "الاندلس", "الروضة", "الخالدية",
    "الزهراء", "السلامة", "النهضة", "النعيم", "المحمدية", "البساتين", "المرجان",
    "الصفا", "ابحر", "الشعيبة", "ذهبان", "الخمرة", "ثول", "طيبة",
    "الرحيلي", "ذهبان الشرقي", "ذهبان الغربي", "خليج سلمان", "بالبيد",
    "الحرازات الشمالية", "الحرازات الجنوبية", "الحرازات", "الفضيله", "الرغامه",
    "السنابل", "التيسير", "تيسير", "الصاله", "النخيل", "الحمراء", "المروه",
    "الربوه", "النزهه", "المشرفه", "الفيحاء", "الصناعيه", "الشماليه", "الشرقيه",
    "الجنوبيه", "الغربيه", "أبحر الشمالية", "أبحر الجنوبية", "الخمرة", "مكه",
    "جده", "الجموم", "بحرة", "الليث", "عسفان", "خليص", "رابغ",

    # ====================== شرق جدة (الشرقية) ======================
    "التوفيق", "المودة", "البيان", "الندى", "الوداد", "الصفوة", "الشناء",
    "الغولاء", "المحمر", "الصفحة", "البدور", "الوفاء", "الرياض", "الفروسية",
    "الحجاز", "الرحمانية", "البشائر", "الفلاح", "الصالحية", "الحمدانية",
    "ام حبلين الشرقية", "الكوثر", "ام حبلين الغربية", "الريان", "الرواسي",
    "التلال", "بريمان", "العسلاء", "المنتزة", "الاجواد", "المنار", "السامر",
    "الحفنة", "الشروق", "الواحة", "مريخ", "النخيل", "القوس", "الرغامة",
    "ام السلم", "المنتزهات", "كنانة", "قبا", "الهزاعية", "العشيرية",
    "الشرقية", "المجد", "رضوى", "البوادر", "ام سدرة", "الهجرة", "العويجاء",
    "الشرائع", "سليته", "المرج", "الشمائل", "البهجة", "المعيلية", "الحرة",
    "العلاء", "الوسامي", "جوهرة ثول", "السلطان", "مخطط واسكان المطار",
    "جامعة جدة", "أبرق الرغامة", "الكرامة", "الرحمة", "البركة", "القرينية",
    "الضاحية", "المليساء", "السرورية", "القوزين", "الوادي", "الساحل",
    "الرابية", "المرسى", "الصناعية الثانية", "الصناعية الثالثة", "العسيلة",
    "الرهناء", "المستقبل", "القاعدة البحرية", "النسيم", "النعيم", "الفيصليه",
    "الرحاب", "البوادي", "الحمدانيه", "الخالديه", "السلامه", "النزهه",
    "الواحه", "الروضه", "السامر", "العدل", "الوادي", "النهضه", "السلام",
    "المرجان", "الصالحيه", "بني مالك", "الرحيلي", "المدائن", "الروابي",
    "الضاحيه", "المنتزهات", "السد",

    # ====================== وسط جدة (الوسطى) ======================
    "الرحاب", "العزيزية", "مشرفة", "بني مالك", "النسيم", "الورود", "الشرفية",
    "الرويس", "السليمانية", "الفيحاء", "الكندرة", "البغدادية", "جدة التاريخية",
    "البلد", "النزهة", "المروة", "الربوة", "البوادي", "الفيصلية", "الثعالبة",
    "المحمدية", "السنابل", "الهنداوية", "غليل", "الصحيفة", "العمارية",
    "البغدادية الغربية", "السبيل", "النزلة اليمانية", "النزلة الشرقية",
    "القريات", "قويزة", "الجامعة", "الثغر", "الفاروق", "مدائن الفهد",
    "الحجاز", "الشرفيه", "المظلوم", "الرويس", "السبيل", "العماريه",
    "الثغر", "البغداديه", "الهنداويه", "الصحيفه", "الوزيريه", "القرينيه",
    "الكندره", "بنى مالك", "الثعالبه", "القوز", "الرحمانيه", "السليمانيه",
    "البساتين", "السناعيه",

    # ====================== جنوب جدة (الجنوبية) ======================
    "الروابي", "الجامعة", "الثغر", "النزلة الشرقية", "الثعالبة", "الفاروق",
    "مدائن الفهد", "النزلة اليمانية", "القريات", "غليل", "بترومين", "الوزيرية",
    "الجوهرة", "الامير عبدالمجيد", "الاجاويد", "الشفا", "الهدا", "السنابل",
    "الاثير", "ابو جعالة", "العسلية", "المستقبل", "السهل", "التضامن",
    "التعاون", "الخمرة", "المحجر", "السرور", "السروات", "الكرامة", "الفضيلة",
    "القرينية", "الضاحية", "الوادي", "الساحل", "الرحمة", "البركة", "المسرة",
    "المليساء", "القوزين", "الرابية", "المرسى", "الرمال", "الموج",
    "الامير فواز الجنوبي", "كيلو 14 الجنوبي", "المنار", "الفلاح", "العدل",
    "السروات", "الشعيبة", "القحمة", "المظلوم", "بني مالك",
}

TO_WORDS_PATTERN = r"(?:الى|الي|الين|لين|الا|ل|to)"

GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام",
    "صباح الخير", "مساء الخير", "هلا", "اهلا", "مرحبا",
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
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
            role TEXT DEFAULT '', registration_date TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS trips (
            trip_id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER,
            customer_id INTEGER, customer_name TEXT, pickup TEXT,
            destination TEXT, trip_type TEXT DEFAULT 'normal',
            original_text TEXT, created_at TEXT, status TEXT DEFAULT 'active')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS ready_drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, trip_id INTEGER,
            driver_id INTEGER, driver_name TEXT, created_at TEXT,
            UNIQUE(trip_id, driver_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS violations (
            user_id INTEGER PRIMARY KEY, count INTEGER DEFAULT 0,
            last_reason TEXT, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY, reason TEXT,
            until_date TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS presence (
            user_id INTEGER PRIMARY KEY, location TEXT,
            last_date TEXT, updated_at TEXT)""")
        self.conn.commit()

    def save_user(self, user):
        self.conn.execute("""
            INSERT INTO users (user_id, name, username, registration_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name, username = excluded.username
        """, (user.id, user.full_name, user.username or "",
              datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()

    def set_role(self, user_id, role):
        self.conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        self.conn.commit()

    def is_banned(self, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT until_date FROM banned_users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return False
        if datetime.now(SAUDI_TZ) > datetime.fromisoformat(row["until_date"]):
            self.conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
            self.conn.commit()
            return False
        return True

    def ban_user(self, user_id, reason, hours=24):
        until = (datetime.now(SAUDI_TZ) + timedelta(hours=hours)).isoformat()
        self.conn.execute("""
            INSERT INTO banned_users (user_id, reason, until_date, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                reason = excluded.reason, until_date = excluded.until_date
        """, (user_id, reason, until, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()

    def unban_user(self, user_id):
        self.conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def create_trip(self, message_id, customer_id, customer_name,
                    pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, customer_name,
                pickup, destination, trip_type, original_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, customer_id, customer_name, pickup, destination,
              trip_type, original_text, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def get_trip(self, trip_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_trip_by_message_id(self, message_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM trips WHERE message_id = ? AND status = 'active'",
                    (message_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def close_trip(self, trip_id):
        self.conn.execute("UPDATE trips SET status = 'closed' WHERE trip_id = ?", (trip_id,))
        self.conn.commit()

    def add_ready_driver(self, trip_id, driver_id, driver_name):
        try:
            self.conn.execute("""
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
        return [dict(r) for r in cur.fetchall()]

    def add_violation(self, user_id, reason):
        cur = self.conn.cursor()
        cur.execute("SELECT count FROM violations WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        count = (row["count"] + 1) if row else 1
        if row:
            self.conn.execute("""
                UPDATE violations SET count = ?, last_reason = ?, updated_at = ?
                WHERE user_id = ?
            """, (count, reason, datetime.now(SAUDI_TZ).isoformat(), user_id))
        else:
            self.conn.execute("""
                INSERT INTO violations (user_id, count, last_reason, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, count, reason, datetime.now(SAUDI_TZ).isoformat()))
        self.conn.commit()
        return count

    def reset_violations(self, user_id):
        self.conn.execute("UPDATE violations SET count = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_presence_today(self, user_id):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM presence WHERE user_id = ? AND last_date = ?",
                    (user_id, today))
        row = cur.fetchone()
        return dict(row) if row else None

    def save_presence(self, user_id, location):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        self.conn.execute("""
            INSERT INTO presence (user_id, location, last_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                location = excluded.location, last_date = excluded.last_date,
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
        self.user_message_times = {}  # لتتبع رسائل المستخدمين ومنع الإزعاج

    def normalize_text(self, text):
        if not text:
            return ""
        text = str(text).lower().replace("ـ", "")
        for old, new in {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي",
                         "ة": "ه", "ؤ": "و", "ئ": "ي"}.items():
            text = text.replace(old, new)
        return re.sub(r"[\u064B-\u065F\u0670]", "", text)

    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def strip_greetings(self, text):
        cleaned = text
        for g in sorted(GREETINGS, key=len, reverse=True):
            cleaned = re.sub(re.escape(g), " ", cleaned, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", cleaned).strip()

    def contains_phone_number(self, text):
        if not text:
            return False
        text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
        compact = re.sub(r"[\s\-\(\)]", "", text)
        patterns = [r"(?<!\d)05\d{8}(?!\d)", r"(?<!\d)5\d{8}(?!\d)",
                    r"(?<!\d)9665\d{8}(?!\d)", r"(?<!\d)\+9665\d{8}(?!\d)"]
        return any(re.search(p, compact) for p in patterns)

    def contains_private_word(self, text):
        normalized = self.normalize_text(text)
        words = re.findall(r"[\w\u0600-\u06FF]+", normalized)
        forbidden = {"خاص", "بالخاص", "للخاص", "خاصني", "خاصك",
                     "خاصه", "بالخاصه", "للخاصه"}
        return any(w in forbidden for w in words)

    def contains_unauthorized_link(self, text):
        if not text:
            return False
        links = re.findall(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)",
                           text.lower())
        for link in links:
            if ALLOWED_GROUP_LINK.lower() in link.replace("https://", "").replace("http://", ""):
                continue
            return True
        return False

    def extract_route(self, text):
        if not text:
            return None, None
        normalized = self.normalize_text(text)
        m = re.search(rf"من\s+(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)", normalized)
        if m:
            p = re.sub(r"[.!،,؟?]+$", "", m.group(1).strip()).strip()
            d = re.sub(r"[.!،,؟?]+$", "", m.group(2).strip()).strip()
            d = re.sub(r"\s+(?:الساعه|الساعة|بعد|قبل)\s+.*$", "", d).strip()
            if p and d:
                return p, d
        m = re.search(rf"^(.+?)\s+{TO_WORDS_PATTERN}\s+(.+)", normalized)
        if m:
            p = re.sub(r"[.!،,؟?]+$", "", m.group(1).strip()).strip()
            d = re.sub(r"[.!،,؟?]+$", "", m.group(2).strip()).strip()
            if p and d:
                return p, d
        found = []
        seen = set()
        for loc in sorted(LOCATIONS_SET, key=lambda x: len(self.normalize_text(x)), reverse=True):
            nloc = self.normalize_text(loc)
            if nloc in normalized and nloc not in seen:
                seen.add(nloc)
                found.append(loc)
        if len(found) >= 2:
            return found[0], found[1]
        return None, None

    def detect_trip(self, text):
        clean = self.strip_greetings(text)
        normalized = self.normalize_text(clean)
        pickup, dest = self.extract_route(clean)
        has_intent = any(self.normalize_text(w) in normalized
                         for w in (NORMAL_TRIP_WORDS + MONTHLY_TRIP_WORDS))
        has_route = bool(pickup and dest)
        if re.search(rf"من\s+.+?\s+{TO_WORDS_PATTERN}\s+.+", normalized):
            has_route = True
        if not has_intent and not has_route:
            return None, None, None
        monthly = any(self.normalize_text(w) in normalized for w in MONTHLY_TRIP_WORDS)
        return ("monthly" if monthly else "normal"), pickup, dest

    def detect_presence(self, text):
        if not text:
            return None
        clean = self.strip_greetings(text)
        normalized = self.normalize_text(clean)

        # استثناء الأسئلة
        for qw in PRESENCE_QUESTION_WORDS:
            nqw = self.normalize_text(qw)
            if re.search(rf"(^|\s){re.escape(nqw)}(\s|$)", normalized):
                if re.search(r"(^|\s)(مين|من|الموجودين|موجودين|المتواجدين)(\s|$)", normalized):
                    return None

        patterns = [
            r"(^|\s)متواجد(\s|$)", r"(^|\s)متواجده(\s|$)", r"(^|\s)متواجدة(\s|$)",
            r"(^|\s)متوفر(\s|$)", r"(^|\s)متوفره(\s|$)", r"(^|\s)متوفرة(\s|$)",
            r"(^|\s)متاح(\s|$)", r"(^|\s)متاحه(\s|$)", r"(^|\s)متاحة(\s|$)",
            r"(^|\s)انا\s+في(\s|$)", r"(^|\s)انا\s+عند(\s|$)",
            r"(^|\s)واقف(\s|$)", r"(^|\s)واقفه(\s|$)", r"(^|\s)واقفة(\s|$)",
            r"(^|\s)في\s+الموقع(\s|$)", r"(^|\s)بالخدمه(\s|$)", r"(^|\s)بالخدمة(\s|$)",
        ]
        if not any(re.search(p, normalized) for p in patterns):
            return None

        # 1. البحث في القائمة الضخمة
        for loc in sorted(LOCATIONS_SET, key=lambda x: len(self.normalize_text(x)), reverse=True):
            if self.normalize_text(loc) in normalized:
                return loc

        # 2. البحث عن "في X" أو "عند X"
        for pattern in [r"(?:في|عند)\s+([^\s،,.!?؟]+)"]:
            m = re.search(pattern, normalized)
            if m:
                w = m.group(1).strip()
                if self.normalize_text(w) in {self.normalize_text(x) for x in LOCATIONS_SET}:
                    return w

        # 3. شبكة الأمان: الالتقاط الذكي لأي موقع ملتصق بـ "بال" أو "ب"
        match_ba = re.search(r"(?:متواجد|متواجده|متواجدين|متوفر|متوفره|متاح|متاحه|واقف|واقفه)\s+(?:بال|ب)([^\s،,.!?؟]+)", normalized)
        if match_ba:
            loc = match_ba.group(1).strip()
            excluded_words = {
                "روح", "روحه", "سرعه", "خدمتك", "خدمتكم", "مشوار", "مشاوير", 
                "اي", "وقت", "ساعه", "يوم", "بكره", "خير", "عافيه", "صحه", "سلامه"
            }
            if self.normalize_text(loc) not in excluded_words:
                return loc

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
        if not message or not user or user.id in ADMIN_IDS:
            return

        count = self.db.add_violation(user.id, reason)
        await self.delete_message(message)

        if count == 1:
            text = (f"⚠️ <b>تنبيه</b>\n\nيا {self.html(user.first_name)}، "
                    f"تم تسجيل المخالفة الأولى.\nالسبب: {self.html(reason)}")
            reply_markup = None
        elif count == 2:
            text = (f"⚠️ <b>تحذير أخير</b>\n\nيا {self.html(user.first_name)}، "
                    f"تم تسجيل المخالفة الثانية.\n⚠️ الثالثة = كتم 24 ساعة.")
            reply_markup = None
        else:
            text = (f"🚫 <b>تم كتمك لمدة 24 ساعة</b>\n\n"
                    f"👤 المستخدم: {self.html(user.first_name)}\n"
                    f"السبب: {self.html(reason)}")
            # إضافة زر إلغاء الكتم للمشرفين فقط
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ إلغاء الكتم (للمشرفين)", callback_data=f"unmute_{user.id}")]
            ])

        try:
            warning = await context.bot.send_message(
                chat_id=message.chat_id, text=text,
                parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            if count < 3 and context.job_queue:
                context.job_queue.run_once(self.delete_later, 8, data=warning)
        except Exception as e:
            logger.error(f"خطأ في إرسال التحذير: {e}")

        if count >= 3:
            try:
                await context.bot.restrict_chat_member(
                    chat_id=message.chat_id, user_id=user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=datetime.now(SAUDI_TZ) + timedelta(hours=24))
                self.db.ban_user(user.id, reason, hours=24)
                self.db.reset_violations(user.id)
            except Exception as e:
                logger.error(f"خطأ في الكتم: {e}")

    async def handle_unmute(self, update, context):
        """معالج زر إلغاء الكتم للمشرفين"""
        query = update.callback_query
        user = query.from_user

        if user.id not in ADMIN_IDS:
            await query.answer("❌ هذا الزر مخصص للإدارة فقط.", show_alert=True)
            return

        try:
            target_id = int(query.data.split("_")[1])
        except Exception:
            await query.answer("❌ حدث خطأ في البيانات.", show_alert=True)
            return

        try:
            # رفع الكتم في تيليجرام
            await context.bot.restrict_chat_member(
                chat_id=GROUP_ID, user_id=target_id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            # إزالة المستخدم من قائمة الحظر في قاعدة البيانات
            self.db.unban_user(target_id)
            
            await query.answer("✅ تم إلغاء الكتم بنجاح.", show_alert=True)
            await query.message.edit_text(
                f"✅ <b>تم إلغاء الكتم</b>\n\n"
                f"👤 المستخدم: <code>{target_id}</code>\n"
                f"👮 بواسطة المشرف: {self.html(user.first_name)}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"خطأ في إلغاء الكتم: {e}")
            await query.answer(f"❌ فشل إلغاء الكتم: {e}", show_alert=True)

    async def send_welcome(self, context, member):
        if member.id in self.welcomed_members:
            return
        self.welcomed_members.add(member.id)
        try:
            self.db.save_user(member)
        except Exception as e:
            logger.error(f"فشل حفظ المستخدم: {e}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"👤 {member.first_name} عميل",
                                  callback_data=f"btn_customer:{member.id}"),
             InlineKeyboardButton(f"🚕 {member.first_name} كابتن",
                                  callback_data=f"btn_driver:{member.id}")],
            [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")],
        ])
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=WELCOME_TEXT + f"\n\n👋 انضم: <b>{self.html(member.first_name)}</b>",
                parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"فشل إرسال الترحيب: {e}")

    async def handle_chat_member(self, update, context):
        cm = update.chat_member
        if not cm or cm.chat.id != GROUP_ID:
            return
        old, new = cm.old_chat_member.status, cm.new_chat_member.status
        if old in ("left", "kicked") and new in ("member", "restricted"):
            u = cm.new_chat_member.user
            if not u.is_bot:
                await self.send_welcome(context, u)

    async def handle_presence(self, update, context, location):
        message, user = update.effective_message, update.effective_user
        self.db.save_user(user)
        if self.db.get_presence_today(user.id):
            await self.issue_violation(update, context,
                                       "تكرار إعلان التواجد أكثر من مرة في اليوم")
            return
        self.db.save_presence(user.id, location)
        await message.reply_text(
            f"📍 <b>تم تسجيل تواجدك</b>\n\n"
            f"🚕 الكابتن: {self.html(user.first_name)}\n"
            f"📍 الموقع: {self.html(location)}",
            parse_mode=ParseMode.HTML)

    async def handle_trip(self, update, context, trip_type, pickup, destination):
        message, user = update.effective_message, update.effective_user
        self.db.save_user(user)
        self.db.set_role(user.id, "customer")
        if not pickup or not destination:
            self.pending_trips[user.id] = {
                "type": trip_type, "pickup": pickup, "destination": destination}
            if not pickup and not destination:
                q = ("📍 <b>من وين إلى وين؟</b>\n\nمثال:\n"
                     "«من الحرازات إلين تيسير»")
            elif not pickup:
                q = (f"📍 <b>ما زال ناقص: من وين تنطلق؟</b>\n\n"
                     f"🏁 الوصول: {self.html(destination)}")
            else:
                q = (f"🏁 <b>ما زال ناقص: إلى وين رايح؟</b>\n\n"
                     f"📍 الانطلاق: {self.html(pickup)}")
            await message.reply_text(q, parse_mode=ParseMode.HTML)
            return
        trip_id = self.db.create_trip(
            message_id=message.message_id, customer_id=user.id,
            customer_name=user.first_name or "العميل",
            pickup=pickup, destination=destination,
            trip_type=trip_type, original_text=message.text or "")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 جاهز", callback_data=f"take_trip:{trip_id}")],
            [InlineKeyboardButton("📩 التواصل مع الكابتن",
                                  callback_data=f"customer_contact:{trip_id}")],
            [InlineKeyboardButton("✅ تم المشوار", callback_data=f"close_trip:{trip_id}")],
        ])
        badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        await message.reply_text(
            f"✅ <b>تم تسجيل طلبك</b>\n\n"
            f"📋 النوع: {badge}\n"
            f"📍 من: {self.html(pickup)}\n"
            f"🏁 إلى: {self.html(destination)}",
            parse_mode=ParseMode.HTML, reply_markup=keyboard)

    async def process_take_trip(self, context, user, trip, from_query=None):
        if user.id == trip["customer_id"]:
            if from_query:
                await from_query.answer("😂 لا يمكنك أخذ مشوارك بنفسك.", show_alert=True)
            return
        self.db.save_user(user)
        self.db.set_role(user.id, "driver")
        added = self.db.add_ready_driver(trip["trip_id"], user.id, user.first_name or "الكابتن")
        if not added:
            if from_query:
                await from_query.answer("⚠️ أنت مسجل بالفعل لهذا المشوار.", show_alert=True)
            return
        if from_query:
            await from_query.answer("✅ تم تسجيل جاهزيتك.", show_alert=True)
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=(f"🚕 <b>كابتن جاهز للمشوار #{trip['trip_id']}</b>\n\n"
                      f"👤 الكابتن: {self.html(user.first_name)}\n\n"
                      f"📍 من: {self.html(trip['pickup'])}\n"
                      f"🏁 إلى: {self.html(trip['destination'])}"),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📩 التواصل مع العميل",
                                          url=f"tg://user?id={trip['customer_id']}")]
                ]))
        except Exception as e:
            logger.error(f"خطأ في إشعار الكابتن: {e}")

    async def handle_take_trip(self, update, context):
        query = update.callback_query
        try:
            trip_id = int(query.data.split(":")[1])
        except Exception:
            await query.answer("❌ حدث خطأ.", show_alert=True)
            return
        trip = self.db.get_trip(trip_id)
        if not trip or trip["status"] != "active":
            await query.answer("❌ المشوار غير متاح.", show_alert=True)
            return
        await self.process_take_trip(context, query.from_user, trip, from_query=query)

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
        buttons = [[InlineKeyboardButton(f"📩 التواصل مع {d['driver_name']}",
                                         url=f"tg://user?id={d['driver_id']}")]
                   for d in drivers]
        await query.answer()
        await query.message.reply_text("🚕 اختر الكابتن للتواصل:",
                                       reply_markup=InlineKeyboardMarkup(buttons))

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
                text=(f"✅ <b>تم إغلاق المشوار #{trip_id}</b>\n\n"
                      f"👤 العميل: {self.html(trip['customer_name'])}\n"
                      f"📍 من: {self.html(trip['pickup'])}\n"
                      f"🏁 إلى: {self.html(trip['destination'])}\n\n"
                      f"شكراً لاستخدامكم مشاوير جدة 🚘"),
                parse_mode=ParseMode.HTML)
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
                    parse_mode=ParseMode.HTML)
            except Exception:
                pass
            return
        if data == "btn_complaints":
            await query.answer()
            await query.message.reply_text(f"⚠️ للتواصل مع الإدارة:\n@{ADMIN_USERNAME}")

    async def handle_message(self, update, context):
        message, user, chat = (update.effective_message, update.effective_user,
                               update.effective_chat)
        if not message or not user or chat.id != GROUP_ID:
            return
        text = message.text or message.caption or ""
        if not text.strip():
            return

        # ====================================================
        # 🛡️ نظام مكافحة الإزعاج (Anti-Flood)
        # ====================================================
        now = time.time()
        times = self.user_message_times.get(user.id, [])
        # الاحتفاظ فقط بالرسائل التي أُرسلت خلال النافذة الزمنية المحددة
        times = [t for t in times if now - t < SPAM_TIME_WINDOW]
        times.append(now)
        self.user_message_times[user.id] = times

        # إذا تجاوز عدد الرسائل الحد المسموح به
        if len(times) > SPAM_MESSAGE_LIMIT:
            self.user_message_times[user.id] = []  # تصفير العداد لمنع التكرار
            await self.issue_violation(
                update, context,
                "إرسال رسائل متكررة بسرعة (إزعاج)"
            )
            return

        logger.info(f"🔥 رسالة | USER={user.id} | TEXT={text}")
        self.db.save_user(user)
        if self.db.is_banned(user.id):
            await self.delete_message(message)
            return
        if self.contains_phone_number(text):
            await self.issue_violation(update, context, "نشر رقم جوال داخل القروب ممنوع")
            return
        if self.contains_private_word(text):
            await self.issue_violation(update, context, "كتابة كلمة «خاص» داخل القروب ممنوعة")
            return
        if self.contains_unauthorized_link(text):
            await self.issue_violation(update, context, "نشر الروابط أو الإعلانات الخارجية ممنوع")
            return
        if user.id in self.pending_trips and text.strip() in ["الغاء", "إلغاء", "كنسل"]:
            del self.pending_trips[user.id]
            await message.reply_text("❌ تم إلغاء الطلب المعلق.")
            return
        presence = self.detect_presence(text)
        if presence is not None:
            if not presence.strip():
                await message.reply_text(
                    "📍 <b>وين موقع تواجدك؟</b>\n\n"
                    "مثال:\n«متواجد في الفضيلة»\n"
                    "أو: «متواجد بالحرازات لأي مشوار»",
                    parse_mode=ParseMode.HTML)
                return
            await self.handle_presence(update, context, presence)
            return
        if message.reply_to_message and "جاهز" in text.strip():
            trip = self.db.get_trip_by_message_id(message.reply_to_message.message_id)
            if trip and trip["status"] == "active":
                await self.process_take_trip(context, user, trip)
                return
        if user.id in self.pending_trips:
            pending = self.pending_trips[user.id]
            new_p, new_d = self.extract_route(text)
            if not new_p or not new_d:
                found, seen = [], set()
                normalized = self.normalize_text(text)
                for loc in sorted(LOCATIONS_SET,
                                  key=lambda x: len(self.normalize_text(x)), reverse=True):
                    nloc = self.normalize_text(loc)
                    if nloc in normalized and nloc not in seen:
                        seen.add(nloc)
                        found.append(loc)
                if len(found) >= 2:
                    new_p, new_d = found[0], found[1]
                elif len(found) == 1:
                    if not pending["pickup"]:
                        new_p = found[0]
                    elif not pending["destination"]:
                        new_d = found[0]
            pickup = pending["pickup"] or new_p
            destination = pending["destination"] or new_d
            if pickup and destination:
                del self.pending_trips[user.id]
                await self.handle_trip(update, context, pending["type"], pickup, destination)
                return
            self.pending_trips[user.id] = {
                "type": pending["type"], "pickup": pickup, "destination": destination}
            if not pickup:
                await message.reply_text("📍 ما زال ناقص: من وين تنطلق؟")
            else:
                await message.reply_text("🏁 ما زال ناقص: إلى وين رايح؟")
            return
        trip_type, pickup, destination = self.detect_trip(text)
        if trip_type:
            await self.handle_trip(update, context, trip_type, pickup, destination)
            return
        normalized = self.normalize_text(text).strip()
        for g in GREETINGS:
            if normalized == self.normalize_text(g):
                await message.reply_text(
                    "وعليكم السلام ورحمة الله وبركاته 🌹\nحياك الله في مشاوير جدة 🚘")
                return

# ============================================================
# 🌐 أوامر
# ============================================================
async def chat_id_command(update, context):
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        text = (f"📌 <b>بيانات القروب</b>\n\n🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
                f"📋 النوع: <code>{chat.type}</code>\n🏷 الاسم: {chat.title or 'بدون اسم'}")
    else:
        text = (f"📌 <b>بيانات المحادثة</b>\n\n🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
                f"📋 النوع: <code>{chat.type}</code>")
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

async def start_command(update, context):
    user = update.effective_user
    bot_instance.db.save_user(user)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 أنا عميل", callback_data=f"btn_customer:{user.id}"),
         InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"btn_driver:{user.id}")],
        [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")],
    ])
    await update.effective_message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.HTML,
                                              reply_markup=keyboard)

async def mybots_command(update, context):
    user = update.effective_user
    await update.effective_message.reply_text(
        f"🤖 <b>حالة البوت</b>\n\n👤 المستخدم: {user.first_name}\n"
        f"🆔 معرفك: <code>{user.id}</code>\n"
        f"📌 معرف القروب: <code>{GROUP_ID}</code>\n✅ البوت يعمل.",
        parse_mode=ParseMode.HTML)

async def error_handler(update, context):
    logger.error("❌ حدث خطأ:", exc_info=context.error)

# ============================================================
# 🚀 التشغيل
# ============================================================
bot_instance = None

def main():
    global bot_instance
    if not TOKEN:
        raise RuntimeError("❌ لم يتم العثور على BOT_TOKEN")
    bot_instance = SmartRidesBot()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chatid", chat_id_command))
    application.add_handler(CommandHandler("mybots", mybots_command))
    application.add_handler(ChatMemberHandler(bot_instance.handle_chat_member,
                                              ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_take_trip,
                                                 pattern=r"^take_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_customer_contact,
                                                 pattern=r"^customer_contact:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_close_trip,
                                                 pattern=r"^close_trip:"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_unmute,
                                                 pattern=r"^unmute_"))
    application.add_handler(CallbackQueryHandler(bot_instance.handle_callback_buttons,
                                                 pattern=r"^btn_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                           bot_instance.handle_message))
    application.add_error_handler(error_handler)
    logger.info("=" * 60)
    logger.info("🚀 تشغيل بوت مشاوير جدة - النسخة النهائية الشاملة")
    logger.info("=" * 60)
    application.run_polling(allowed_updates=Update.ALL_TYPES,
                            drop_pending_updates=True)

if __name__ == "__main__":
    main()
