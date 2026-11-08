"""
🤖 بوت مشاوير جدة - النسخة المصححة (v2)
- «السلام» تُعامل كتحية فقط في بداية الرسالة (لا تكسر حي السلام).
- «خاص» لا تعطي مخالفة لعبارة مثل «سيارة خاصة».
- الطلب المعلّق لا يبتلع الرسائل العادية.
- حي واحد مع «من» أو «إلى» يُلتقط ويُسأل عن الناقص فقط.
- استثناءات التواجد تعمل بشكل صحيح.
- «جامعة جدة» لا تحوّل الطلب إلى شهري.
- فحص روابط دقيق (النطاق + المسار + الروابط المخفية).
- عرض أسماء الأحياء بالإملاء الأصلي الذي كتبه العضو.
"""

import os
import re
import time
import asyncio
import logging
import sqlite3

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, filters,
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
ALLOWED_SLUG = ALLOWED_GROUP_LINK.split("/")[-1].lower()
SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"
PENDING_TTL = 600  # مدة انتظار إكمال الطلب الناقص (ثواني)
WELCOME_COOLDOWN = 120  # منع تكرار الترحيب لنفس العضو (ثواني)

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
"""

# ============================================================
# 🔤 أدوات النصوص
# ============================================================
_NORM_MAP = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}


def norm(text):
    """توحيد النص العربي (همزات، تاء مربوطة، تشكيل...)."""
    if not text:
        return ""
    text = str(text).lower().replace("ـ", "")
    for old, new in _NORM_MAP.items():
        text = text.replace(old, new)
    return re.sub(r"[\u064B-\u065F\u0670]", "", text)


# سوابق مسموحة قبل الكلمة (و، ف، ب، ل، ك، ال)
_PREFIX = r"(?:و|ف|ب|ل|ك|ال)?"


def words_re(words, prefix=True):
    alt = "|".join(re.escape(norm(w)) for w in sorted(set(words), key=len, reverse=True))
    pre = _PREFIX if prefix else ""
    return re.compile(rf"(?<!\w){pre}(?:{alt})(?!\w)")


# ============================================================
# 📚 الكلمات
# ============================================================
MONTHLY_TRIP_WORDS = [
    "شهري", "شهرية", "شهريا", "بالشهر", "دوام", "مدرسة", "جامعة", "التزام",
    "اسبوعي", "أسبوعي", "يومي", "يوميا", "مشوار يومي", "توصيل يومي",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "مشاوير", "توصيل", "توصيله", "يوصلني", "يوديني", "ابغى مشوار",
    "ابي مشوار", "ابغا مشوار", "احتاج توصيل", "محتاج توصيل", "من يوصلني",
    "اوصلني", "ودني", "خذني", "ابي اروح", "ابغى اروح", "ابغا اروح",
]

PRESENCE_QUESTION_WORDS = ["مين", "وين", "الموجودين", "موجودين", "المتواجدين", "الموجود", "كم"]

GREETINGS = [
    "السلام عليكم", "سلام عليكم", "السلام", "سلام",
    "صباح الخير", "مساء الخير", "هلا", "اهلا", "مرحبا",
]

# «السلام/سلام» وحدها هي أيضاً اسم حي، فلا تُحذف من وسط النص.
# تُحذف فقط التحيات الصريحة، وفقط من بداية الرسالة.
_GREET_PHRASES = [g for g in GREETINGS if norm(g) not in ("السلام", "سلام")]

NORMAL_RE = words_re(NORMAL_TRIP_WORDS)
MONTHLY_RE = words_re(MONTHLY_TRIP_WORDS)
QUESTION_RE = words_re(PRESENCE_QUESTION_WORDS, prefix=False)
GREETINGS_RE = re.compile(
    r"^\s*(?:و?(?:"
    + "|".join(re.escape(norm(g)) for g in sorted(_GREET_PHRASES, key=len, reverse=True))
    + r")(?!\w)[\s،,.!]*)+")

STRONG_PRESENCE_RE = re.compile(
    r"(?<!\w)(?:متواجد|متواجده|متواجدين|متوفر|متوفره|متاح|متاحه|بالخدمه)(?!\w)")
WEAK_PRESENCE_RE = re.compile(r"(?<!\w)(?:انا\s+(?:في|عند)|واقفه?|في\s+الموقع)(?!\w)")
PRESENCE_NET_RE = re.compile(
    r"(?:متواجد|متواجده|متواجدين|متوفر|متوفره|متاح|متاحه|واقف|واقفه)\s+"
    r"(?:في\s+|عند\s+|بال|ب)([^\s،,.!?؟]+)")
PRESENCE_EXCLUDED_RAW = {
    "روح", "روحه", "سرعه", "خدمتك", "خدمتكم", "الخدمه", "مشوار", "مشاوير",
    "اي", "وقت", "ساعه", "يوم", "بكره", "خير", "عافيه", "صحه", "سلامه",
    "البيت", "المنزل", "الشغل", "العمل", "السياره", "هنا", "الان",
}


def _strip_pfx(w):
    """يزيل «ال» أو «ب» من أول الكلمة للمقارنة."""
    if w.startswith("ال") and len(w) > 2:
        return w[2:]
    if w.startswith("ب") and len(w) > 2:
        return w[1:]
    return w


PRESENCE_EXCLUDED = {_strip_pfx(w) for w in PRESENCE_EXCLUDED_RAW}

# أحياء جدة ومناطقها (يُكتب كل اسم مرة واحدة، والمطابقة بعد التوحيد)
_LOCATIONS_RAW = """
الاصالة, ابحر الشمالية, ابحر الجنوبية, ابحر, الفردوس, الشراع, الامواج, الصواري, الياقوت, اللؤلؤ,
مطار الملك عبدالعزيز, الزمرد, المنارات, الفنار, البحيرات, النور, المروج, الخليج, النجمة, الزهور,
الشويضي, الغدير, الربيع, العقيق, العبير, الدرة, طابة, المجامع, المزيرعة, الفرقان, اليسر, الجزيرة,
الكورنيش, المعرفة, الودية, الشاطئ, الحمراء, الاندلس, الروضة, الخالدية, الزهراء, السلامة, النهضة,
النعيم, المحمدية, البساتين, المرجان, الصفا, الشعيبة, ذهبان, ذهبان الشرقي, ذهبان الغربي, الخمرة,
ثول, طيبة, الرحيلي, خليج سلمان, الحرازات الشمالية, الحرازات الجنوبية, الحرازات, الفضيلة,
الرغامة, السنابل, التيسير, تيسير, الصالة, النخيل, المروة, الربوة, النزهة, المشرفة, الفيحاء,
الصناعية, مكة, الجموم, بحرة, الليث, عسفان, خليص, رابغ,
التوفيق, المودة, البيان, الندى, الوداد, الصفوة, الشناء, الغولاء, المحمر, الصفحة, البدور, الوفاء,
الرياض, الفروسية, الحجاز, الرحمانية, البشائر, الفلاح, الصالحية, الحمدانية, ام حبلين الشرقية,
ام حبلين الغربية, الكوثر, الريان, الرواسي, التلال, بريمان, العسلاء, المنتزة, الاجواد, المنار,
السامر, الحفنة, الشروق, الواحة, مريخ, القوس, ام السلم, المنتزهات, كنانة, قبا, الهزاعية, العشيرية,
المجد, رضوى, البوادر, ام سدرة, الهجرة, العويجاء, الشرائع, سليته, المرج, الشمائل, البهجة,
المعيلية, الحرة, العلاء, الوسامي, جوهرة ثول, السلطان, مخطط واسكان المطار, جامعة جدة,
ابرق الرغامة, الكرامة, الرحمة, البركة, القرينية, الضاحية, المليساء, السرورية, القوزين, الوادي,
الساحل, الرابية, المرسى, الصناعية الثانية, الصناعية الثالثة, العسيلة, الرهناء, المستقبل,
القاعدة البحرية, النسيم, الفيصلية, الرحاب, البوادي, العدل, السلام, بني مالك, المدائن, الروابي, السد,
العزيزية, مشرفة, الورود, الشرفية, الرويس, السليمانية, الكندرة, البغدادية, جدة التاريخية, البلد,
الثعالبة, الهنداوية, غليل, الصحيفة, العمارية, البغدادية الغربية, السبيل, النزلة اليمانية,
النزلة الشرقية, القريات, قويزة, الجامعة, الثغر, الفاروق, مدائن الفهد, المظلوم, الوزيرية, القوز,
بترومين, الجوهرة, الامير عبدالمجيد, الاجاويد, الشفا, الهدا, الاثير, ابو جعالة, العسلية, السهل,
التضامن, التعاون, المحجر, السرور, السروات, المسرة, الرمال, الموج, الامير فواز الجنوبي,
كيلو 14 الجنوبي, القحمة
"""

LOC_INDEX = {}  # الاسم الموحّد -> الاسم الأصلي للعرض
for _loc in _LOCATIONS_RAW.replace("\n", " ").split(","):
    _loc = _loc.strip()
    if _loc:
        LOC_INDEX.setdefault(norm(_loc), _loc)


def _build_loc_patterns():
    patterns = []
    for key in sorted(LOC_INDEX, key=len, reverse=True):
        body = re.escape(key)
        alt = f"{_PREFIX}{body}"
        if key.startswith("ال") and len(key) > 2:
            alt += "|لل" + re.escape(key[2:])  # للفضيلة = ل + الفضيلة
        patterns.append((re.compile(rf"(?<!\w)(?:{alt})(?!\w)"), key))
    return patterns


LOC_PATTERNS = _build_loc_patterns()


def find_locations(normalized):
    """يرجع [(start, end, name)] مرتبة حسب مكانها في النص، بدون تداخل."""
    taken, found = [], []
    for pat, key in LOC_PATTERNS:
        for m in pat.finditer(normalized):
            s, e = m.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            taken.append((s, e))
            found.append((s, e, LOC_INDEX[key]))
    found.sort()
    return found


def unique_names(locs):
    names = []
    for _, _, name in locs:
        if name not in names:
            names.append(name)
    return names


def remove_locations(normalized):
    """يحذف مواضع الأحياء من النص (حتى لا تُحسب كلمات مثل «جامعة» من اسم الحي)."""
    out = normalized
    for s, e, _ in sorted(find_locations(normalized), reverse=True):
        out = out[:s] + " " + out[e:]
    return out


_TO_WORDS = ("الي", "الين", "لين", "ل", "to")
_TO = r"(?:الي|الين|لين|ل|to)"
EXPLICIT_ROUTE_RE = re.compile(rf"(?<!\w)من\s+(.+?)\s+{_TO}\s+(.+)")
IMPLICIT_ROUTE_RE = re.compile(rf"^(.+?)\s+{_TO}\s+(.+)$")
_STOP_RE = re.compile(
    r"\s+(?:الساعه|ساعه|بعد|قبل|الان|بكره|بكرا|اليوم|الليله|الصبح|ابغي|ابغا|ابي|"
    r"محتاج|احتاج|مشوار|توصيل|لو|فضلا|الله)(?!\w).*$")
_PLACE_STOPWORDS = {"لا", "ايوه", "ايوا", "تمام", "اوكي", "ok", "شكرا", "طيب", "هلا", "نعم"}
_EDGE_PUNCT = ".,!?؟،:;"


def clean_place(seg):
    seg = _STOP_RE.sub("", (seg or "").strip())
    return re.sub(r"^[\s.!،,؟?]+|[\s.!،,؟?]+$", "", seg)


def pick_place(seg, last):
    locs = find_locations(seg)
    if locs:
        return (locs[-1] if last else locs[0])[2]
    words = clean_place(seg).split()
    if not words:
        return None
    words = words[-3:] if last else words[:3]
    return " ".join(words)


def restore_display(original, place):
    """يرجع اسم المكان بإملاء العضو الأصلي (قبل التوحيد) إن أمكن."""
    if not place:
        return place
    pw = place.split()
    if not pw:
        return place
    toks = [t.strip(_EDGE_PUNCT) for t in (original or "").split()]
    toks = [t for t in toks if t]
    nt = [norm(t) for t in toks]
    for i in range(len(toks) - len(pw) + 1):
        if nt[i:i + len(pw)] == pw:
            return " ".join(toks[i:i + len(pw)])
    return place


def marker_role(n, loc):
    """يحدد دور حي واحد: «من X» = انطلاق، «إلى/ل X» = وصول، غير ذلك None."""
    s, e, name = loc
    seg = n[s:e]
    key = norm(name)
    if seg.startswith("لل") or (seg.startswith("ل") and not key.startswith("ل")):
        return "dest"
    prev = n[:s].split()[-1:]
    if prev:
        if prev[0] == "من":
            return "pickup"
        if prev[0] in _TO_WORDS:
            return "dest"
    return None


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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trips_msg ON trips(message_id)")
        self.conn.commit()

    @staticmethod
    def now():
        return datetime.now(SAUDI_TZ).isoformat()

    def save_user(self, user):
        self.conn.execute("""
            INSERT INTO users (user_id, name, username, registration_date)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name, username = excluded.username
        """, (user.id, user.full_name, user.username or "", self.now()))
        self.conn.commit()

    def get_user(self, user_id):
        row = self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def set_role(self, user_id, role):
        # upsert: يعمل حتى لو العضو غير مسجل مسبقاً
        self.conn.execute("""
            INSERT INTO users (user_id, role, registration_date) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
        """, (user_id, role, self.now()))
        self.conn.commit()

    def get_role(self, user_id):
        row = self.conn.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["role"] if row else ""

    def is_banned(self, user_id):
        row = self.conn.execute(
            "SELECT until_date FROM banned_users WHERE user_id = ?", (user_id,)).fetchone()
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
        """, (user_id, reason, until, self.now()))
        self.conn.commit()

    def create_trip(self, message_id, customer_id, customer_name,
                    pickup, destination, trip_type, original_text):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO trips (message_id, customer_id, customer_name,
                pickup, destination, trip_type, original_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, customer_id, customer_name, pickup, destination,
              trip_type, original_text, self.now()))
        self.conn.commit()
        return cur.lastrowid

    def get_trip(self, trip_id):
        row = self.conn.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
        return dict(row) if row else None

    def get_trip_by_message_id(self, message_id):
        row = self.conn.execute(
            "SELECT * FROM trips WHERE message_id = ? AND status = 'active'",
            (message_id,)).fetchone()
        return dict(row) if row else None

    def close_trip(self, trip_id):
        self.conn.execute("UPDATE trips SET status = 'closed' WHERE trip_id = ?", (trip_id,))
        self.conn.commit()

    def add_ready_driver(self, trip_id, driver_id, driver_name):
        try:
            self.conn.execute("""
                INSERT INTO ready_drivers (trip_id, driver_id, driver_name, created_at)
                VALUES (?, ?, ?, ?)
            """, (trip_id, driver_id, driver_name, self.now()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_ready_drivers(self, trip_id):
        rows = self.conn.execute(
            "SELECT * FROM ready_drivers WHERE trip_id = ? ORDER BY id ASC", (trip_id,)).fetchall()
        return [dict(r) for r in rows]

    def add_violation(self, user_id, reason):
        row = self.conn.execute(
            "SELECT count FROM violations WHERE user_id = ?", (user_id,)).fetchone()
        count = (row["count"] + 1) if row else 1
        self.conn.execute("""
            INSERT INTO violations (user_id, count, last_reason, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                count = excluded.count, last_reason = excluded.last_reason,
                updated_at = excluded.updated_at
        """, (user_id, count, reason, self.now()))
        self.conn.commit()
        return count

    def reset_violations(self, user_id):
        self.conn.execute("UPDATE violations SET count = 0 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_presence_today(self, user_id):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        row = self.conn.execute(
            "SELECT * FROM presence WHERE user_id = ? AND last_date = ?",
            (user_id, today)).fetchone()
        return dict(row) if row else None

    def save_presence(self, user_id, location):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        self.conn.execute("""
            INSERT INTO presence (user_id, location, last_date, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                location = excluded.location, last_date = excluded.last_date,
                updated_at = excluded.updated_at
        """, (user_id, location, today, self.now()))
        self.conn.commit()


# ============================================================
# 🤖 البوت
# ============================================================
# أفعال تدل أن «خاص» المقصود بها المراسلة الخاصة
_DM_VERBS = {"راسلني", "كلمني", "ارسل", "ارسلي", "تواصل", "كلم", "راسل",
             "ابعث", "ابعثلي", "ارسلني", "كلمنا", "راسلونا", "تعال", "ابشر", "ردي", "رد"}
_PRIVATE_EXPLICIT = {"بالخاص", "للخاص", "خاصني", "خاصك", "بالخاصه", "للخاصه"}
_PRIVATE_BARE = {"خاص", "خاصه"}


class SmartRidesBot:
    def __init__(self):
        self.db = Database()
        self.pending_trips = {}
        self.welcomed = {}  # user_id -> وقت آخر ترحيب
        self._tasks = set()

    # ---------------- أدوات ----------------
    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def mention(self, user_id, name):
        return f'<a href="tg://user?id={user_id}">{self.html(name or "المستخدم")}</a>'

    def contact_url(self, user_id):
        u = self.db.get_user(user_id)
        if u and u.get("username"):
            return f"https://t.me/{u['username']}"
        return f"tg://user?id={user_id}"

    def strip_greetings(self, text):
        """يرجع النص موحّداً وبدون التحيات من بداية الرسالة."""
        cleaned = GREETINGS_RE.sub(" ", norm(text), count=1)
        return re.sub(r"\s+", " ", cleaned).strip()

    def contains_phone_number(self, text):
        if not text:
            return False
        text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"))
        compact = re.sub(r"[\s\-\(\)\.]", "", text)
        patterns = [r"(?<!\d)05\d{8}(?!\d)", r"(?<!\d)5\d{8}(?!\d)",
                    r"(?<!\d)(?:\+|00)?9665\d{8}(?!\d)"]
        return any(re.search(p, compact) for p in patterns)

    def contains_private_word(self, text):
        words = re.findall(r"[\w\u0600-\u06FF]+", norm(text))
        if any(w in _PRIVATE_EXPLICIT for w in words):
            return True
        # «خاص» وحدها: مخالفة فقط لو هي الكلمة الوحيدة أو جاءت بعد فعل مراسلة
        # (حتى لا تُعاقب عبارة مثل «سيارة خاصة» أو «مشوار خاص»)
        for i, w in enumerate(words):
            if w in _PRIVATE_BARE:
                if len(words) == 1 or (i > 0 and words[i - 1] in _DM_VERBS):
                    return True
        return False

    @staticmethod
    def link_allowed(link):
        l = link.strip().lower().rstrip(").,!؟،")
        l = re.sub(r"^https?://", "", l)
        l = re.sub(r"^www\.", "", l)
        m = re.match(r"^(?:t\.me|telegram\.me|telegram\.dog)/([^/?#]+)", l)
        return bool(m and m.group(1) == ALLOWED_SLUG)

    def contains_unauthorized_link(self, text, message=None):
        candidates = []
        if text:
            candidates += re.findall(
                r"(?<![\w./@-])(?:https?://|www\.|t\.me/|telegram\.me/|telegram\.dog/)\S+",
                text, flags=re.I)
        if message is not None:  # الروابط المخفية خلف نص + الروابط التي تعرّف عليها تيليجرام
            try:
                ents = {}
                ents.update(message.parse_entities())
                ents.update(message.parse_caption_entities())
                for ent, ent_text in ents.items():
                    if ent.type == "text_link" and ent.url:
                        candidates.append(ent.url)
                    elif ent.type == "url":
                        candidates.append(ent_text)
            except Exception as e:
                logger.warning(f"تعذر فحص entities: {e}")
        return any(not self.link_allowed(c) for c in candidates)

    # ---------------- كشف الرحلات ----------------
    def extract_route(self, text, loose=False):
        """يرجع (انطلاق، وصول) أو (None, None).
        loose=True يسمح بالتقاط حيّين من النص بدون «من/إلى» (يُستخدم مع وجود نيّة طلب)."""
        n = self.strip_greetings(text)
        m = EXPLICIT_ROUTE_RE.search(n)
        if m:
            p = pick_place(m.group(1), last=True)
            d = pick_place(m.group(2), last=False)
            if p and d:
                return p, d
        m = IMPLICIT_ROUTE_RE.match(n)
        if m and find_locations(m.group(1)) and find_locations(m.group(2)):
            return pick_place(m.group(1), True), pick_place(m.group(2), False)
        if loose:
            names = unique_names(find_locations(n))
            if len(names) >= 2:
                return names[0], names[1]
        return None, None

    def detect_trip(self, text):
        n = self.strip_greetings(text)
        if not n:
            return None, None, None
        locs = find_locations(n)
        normal = bool(NORMAL_RE.search(n))
        # «جامعة» داخل اسم حي («جامعة جدة») لا تعني مشواراً شهرياً
        monthly = bool(MONTHLY_RE.search(remove_locations(n)))
        intent = normal or (monthly and bool(locs))
        pickup, dest = self.extract_route(n, loose=intent)

        if intent and not (pickup and dest) and len(locs) == 1:
            role = marker_role(n, locs[0])
            if role == "pickup":
                pickup = locs[0][2]
            elif role == "dest":
                dest = locs[0][2]

        if not intent:
            # بدون كلمة طلب: لازم مسار كامل وأحد طرفيه حي معروف
            if not (pickup and dest):
                return None, None, None
            if not (find_locations(norm(pickup)) or find_locations(norm(dest))):
                return None, None, None

        pickup = restore_display(text, pickup)
        dest = restore_display(text, dest)
        return ("monthly" if monthly else "normal"), pickup, dest

    def detect_presence(self, text):
        """None = ليست تواجد | "" = تواجد بدون موقع | نص = الموقع."""
        if not text or "؟" in text or "?" in text:
            return None
        n = self.strip_greetings(text)
        if not n or QUESTION_RE.search(n):
            return None
        strong = STRONG_PRESENCE_RE.search(n)
        weak = WEAK_PRESENCE_RE.search(n)
        if not strong and not weak:
            return None

        locs = find_locations(n)
        if locs:
            if strong or not NORMAL_RE.search(n):
                return locs[0][2]
            return None
        if not strong:
            return None  # صيغة ضعيفة بدون حي معروف: تجاهل

        # شبكة الأمان: حي غير مدرج بعد «متواجد بـ / في»
        m = PRESENCE_NET_RE.search(n)
        if m:
            loc = m.group(1).strip()
            if loc and _strip_pfx(loc) not in PRESENCE_EXCLUDED:
                # نرجع الإملاء الأصلي إن أمكن
                for t in re.findall(r"[^\s،,.!?؟]+", text):
                    nt = norm(t)
                    if nt.endswith(loc) and 0 <= len(nt) - len(loc) <= 3 and len(t) == len(nt):
                        return t[len(t) - len(loc):]
                return loc
        return ""

    # ---------------- حذف / مخالفات ----------------
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

    async def _delayed_delete(self, msg, delay):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception:
            pass

    def schedule_delete(self, context, msg, delay=8):
        """يحذف الرسالة بعد مدة (يعمل حتى بدون job-queue)."""
        if context.job_queue:
            context.job_queue.run_once(self.delete_later, delay, data=msg)
        else:
            task = asyncio.create_task(self._delayed_delete(msg, delay))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

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
        elif count == 2:
            text = (f"⚠️ <b>تحذير أخير</b>\n\nيا {self.html(user.first_name)}، "
                    f"تم تسجيل المخالفة الثانية.\n⚠️ الثالثة = كتم 24 ساعة.")
        else:
            text = f"🚫 <b>تم كتمك لمدة 24 ساعة</b>\n\nالسبب: {self.html(reason)}"
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
                text = (f"⚠️ <b>تحذير</b>\n\nيا {self.html(user.first_name)}، "
                        f"تكررت المخالفة.\nالسبب: {self.html(reason)}")
        try:
            warning = await context.bot.send_message(
                chat_id=message.chat_id, text=text, parse_mode=ParseMode.HTML)
            self.schedule_delete(context, warning, 8)
        except Exception as e:
            logger.error(f"خطأ في إرسال التحذير: {e}")

    # ---------------- الترحيب ----------------
    def _recently_welcomed(self, user_id):
        now = time.time()
        last = self.welcomed.get(user_id)
        if last and now - last < WELCOME_COOLDOWN:
            return True
        self.welcomed[user_id] = now
        # تنظيف الذاكرة
        if len(self.welcomed) > 2000:
            self.welcomed = {k: v for k, v in self.welcomed.items()
                             if now - v < WELCOME_COOLDOWN}
        return False

    async def send_welcome(self, context, member):
        # يمنع التكرار بين chat_member و new_chat_members، ويسمح بالترحيب عند العودة لاحقاً
        if self._recently_welcomed(member.id):
            return
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

    async def handle_new_members(self, update, context):
        """احتياط: لو ما وصل تحديث chat_member."""
        msg = update.effective_message
        if not msg or msg.chat_id != GROUP_ID:
            return
        for m in msg.new_chat_members or []:
            if not m.is_bot:
                await self.send_welcome(context, m)

    # ---------------- التواجد ----------------
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

    # ---------------- المشاوير ----------------
    def get_pending(self, user_id):
        p = self.pending_trips.get(user_id)
        if not p:
            return None
        if time.time() - p["ts"] > PENDING_TTL:
            del self.pending_trips[user_id]
            return None
        return p

    async def ask_missing(self, message, pickup, destination, detailed=True):
        if not pickup and not destination:
            q = ("📍 <b>من وين إلى وين؟</b>\n\nمثال:\n«من الحرازات إلين تيسير»")
        elif not pickup:
            q = (f"📍 <b>ما زال ناقص: من وين تنطلق؟</b>\n\n"
                 f"🏁 الوصول: {self.html(destination)}")
        else:
            q = (f"🏁 <b>ما زال ناقص: إلى وين رايح؟</b>\n\n"
                 f"📍 الانطلاق: {self.html(pickup)}")
        await message.reply_text(q, parse_mode=ParseMode.HTML)

    async def handle_trip(self, update, context, trip_type, pickup, destination):
        message, user = update.effective_message, update.effective_user
        self.db.save_user(user)
        self.db.set_role(user.id, "customer")
        if not pickup or not destination:
            self.pending_trips[user.id] = {
                "type": trip_type, "pickup": pickup, "destination": destination,
                "ts": time.time()}
            await self.ask_missing(message, pickup, destination)
            return
        trip_id = self.db.create_trip(
            message_id=message.message_id, customer_id=user.id,
            customer_name=user.first_name or "العميل",
            pickup=pickup, destination=destination,
            trip_type=trip_type, original_text=message.text or message.caption or "")
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

    async def try_complete_pending(self, update, context, pending, text, is_reply_to_bot):
        """يحاول إكمال طلب ناقص. يرجع True إذا تعامل مع الرسالة، False إذا لا علاقة لها."""
        message, user = update.effective_message, update.effective_user
        n = self.strip_greetings(text)
        old_p, old_d = pending["pickup"], pending["destination"]
        pickup, destination = old_p, old_d

        new_p, new_d = self.extract_route(text, loose=True)
        if new_p and new_d:
            pickup, destination = new_p, new_d
        else:
            locs = find_locations(n)
            names = unique_names(locs)
            if len(names) >= 2:
                if not pickup and not destination:
                    pickup, destination = names[0], names[1]
                elif not pickup:
                    pickup = names[0]
                else:
                    destination = names[-1]
            elif len(locs) == 1:
                name = locs[0][2]
                role = marker_role(n, locs[0])
                if role == "pickup":
                    pickup = name
                elif role == "dest":
                    destination = name
                elif not pickup:
                    pickup = name
                else:
                    destination = name
            elif is_reply_to_bot:
                # حي غير مدرج: نقبله فقط لو كان رداً مباشراً على سؤال البوت
                raw = clean_place(n)
                if 0 < len(raw.split()) <= 3 and raw not in _PLACE_STOPWORDS:
                    if not pickup:
                        pickup = raw
                    else:
                        destination = raw

        if pickup != old_p:
            pickup = restore_display(text, pickup)
        if destination != old_d:
            destination = restore_display(text, destination)

        if pickup and destination:
            del self.pending_trips[user.id]
            await self.handle_trip(update, context, pending["type"], pickup, destination)
            return True

        if (pickup, destination) != (old_p, old_d):
            self.pending_trips[user.id] = {
                "type": pending["type"], "pickup": pickup,
                "destination": destination, "ts": time.time()}
            await self.ask_missing(message, pickup, destination)
            return True

        if is_reply_to_bot:
            await self.ask_missing(message, pickup, destination)
            return True
        return False  # رسالة عادية لا علاقة لها بالطلب المعلق

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

        text = (f"🚕 <b>كابتن جاهز للمشوار #{trip['trip_id']}</b>\n\n"
                f"👤 الكابتن: {self.html(user.first_name)}\n\n"
                f"📍 من: {self.html(trip['pickup'])}\n"
                f"🏁 إلى: {self.html(trip['destination'])}")
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
            "📩 التواصل مع العميل", url=self.contact_url(trip["customer_id"]))]])
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML,
                reply_markup=keyboard)
        except TelegramError as e:
            # غالباً خصوصية المستخدم تمنع زر tg://user → نرسل بمنشن نصي
            logger.warning(f"فشل إرسال الزر، سيتم استخدام منشن نصي: {e}")
            try:
                await context.bot.send_message(
                    chat_id=GROUP_ID, parse_mode=ParseMode.HTML,
                    text=text + f"\n\n📩 العميل: "
                                f"{self.mention(trip['customer_id'], trip['customer_name'])}")
            except Exception as e2:
                logger.error(f"خطأ في إشعار الكابتن: {e2}")

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
        await query.answer()
        chat_id = update.effective_chat.id
        buttons = [[InlineKeyboardButton(f"📩 التواصل مع {d['driver_name']}",
                                         url=self.contact_url(d["driver_id"]))]
                   for d in drivers]
        try:
            await context.bot.send_message(
                chat_id=chat_id, text="🚕 اختر الكابتن للتواصل:",
                reply_markup=InlineKeyboardMarkup(buttons))
        except TelegramError as e:
            logger.warning(f"فشل أزرار الكباتن، سيتم استخدام منشن نصي: {e}")
            lines = "\n".join(f"🚕 {self.mention(d['driver_id'], d['driver_name'])}"
                              for d in drivers)
            await context.bot.send_message(
                chat_id=chat_id, parse_mode=ParseMode.HTML,
                text=f"🚕 <b>الكباتن الجاهزون:</b>\n{lines}")

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
        if query.from_user.id != trip["customer_id"] and query.from_user.id not in ADMIN_IDS:
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

        if data.startswith(("btn_customer:", "btn_driver:")):
            role = "customer" if data.startswith("btn_customer:") else "driver"
            try:
                target_id = int(data.split(":")[1])
            except Exception:
                await query.answer("❌ حدث خطأ.", show_alert=True)
                return
            # العضو نفسه أو الإدارة فقط
            if user.id != target_id and user.id not in ADMIN_IDS:
                await query.answer("❌ هذا الزر غير مخصص لك.", show_alert=True)
                return
            if user.id == target_id:
                self.db.save_user(user)
            self.db.set_role(target_id, role)
            role_text = "عميل 👤" if role == "customer" else "كابتن 🚕"
            await query.answer(f"✅ تم تسجيلك كـ {role_text}"
                               if user.id == target_id
                               else f"✅ تم تحديد العضو كـ {role_text}", show_alert=True)
            try:  # نخفي أزرار الدور ونبقي زر الشكاوى
                await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")]]))
            except Exception:
                pass
            return

        if data == "btn_complaints":
            await query.answer()
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ للتواصل مع الإدارة:\n@{ADMIN_USERNAME}")
            except Exception as e:
                logger.error(f"خطأ في زر الشكاوى: {e}")
            return

        logger.warning(f"زر غير معروف: {data}")
        await query.answer()

    # ---------------- الرسائل ----------------
    async def handle_message(self, update, context):
        message, user, chat = (update.effective_message, update.effective_user,
                               update.effective_chat)
        if not message or not user or not chat or chat.id != GROUP_ID:
            return
        text = message.text or message.caption or ""
        if not text.strip():
            return
        is_edit = update.edited_message is not None
        # لا نسجل نص الرسائل (خصوصية)
        logger.info(f"رسالة | USER={user.id} | EDIT={is_edit} | LEN={len(text)}")

        self.db.save_user(user)
        if self.db.is_banned(user.id):
            await self.delete_message(message)
            return

        # --- المخالفات (تشمل الرسائل المعدّلة) ---
        if self.contains_phone_number(text):
            await self.issue_violation(update, context, "نشر رقم جوال داخل القروب ممنوع")
            return
        if self.contains_private_word(text):
            await self.issue_violation(update, context, "كتابة كلمة «خاص» داخل القروب ممنوعة")
            return
        if self.contains_unauthorized_link(text, message):
            await self.issue_violation(update, context, "نشر الروابط أو الإعلانات الخارجية ممنوع")
            return

        # الرسائل المعدّلة: فحص المخالفات فقط (لا تسجيل مشاوير/تواجد مكرر)
        if is_edit:
            return

        # --- إلغاء الطلب المعلق ---
        pending = self.get_pending(user.id)
        if pending and norm(text).strip() in {"الغاء", "كنسل"}:
            del self.pending_trips[user.id]
            await message.reply_text("❌ تم إلغاء الطلب المعلق.")
            return

        # --- التواجد ---
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

        # --- كابتن يقتبس الطلب ويكتب «جاهز» ---
        if message.reply_to_message and "جاهز" in text:
            trip = self.db.get_trip_by_message_id(message.reply_to_message.message_id)
            if trip and trip["status"] == "active":
                await self.process_take_trip(context, user, trip)
                return

        # --- إكمال طلب ناقص ---
        if pending:
            rt = message.reply_to_message
            is_reply_to_bot = bool(rt and rt.from_user and rt.from_user.id == context.bot.id)
            if await self.try_complete_pending(update, context, pending, text, is_reply_to_bot):
                return

        # --- طلب مشوار جديد ---
        trip_type, pickup, destination = self.detect_trip(text)
        if trip_type:
            await self.handle_trip(update, context, trip_type, pickup, destination)
            return

        # --- تحية ---
        n = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", norm(text))).strip()
        if n in {norm(g) for g in GREETINGS}:
            if "صباح" in n:
                reply = "صباح النور والسرور ☀️\nحياك الله في مشاوير جدة 🚘"
            elif "مساء" in n:
                reply = "مساء النور والسرور 🌙\nحياك الله في مشاوير جدة 🚘"
            elif "سلام" in n:
                reply = "وعليكم السلام ورحمة الله وبركاته 🌹\nحياك الله في مشاوير جدة 🚘"
            else:
                reply = "هلا والله 🌹\nحياك الله في مشاوير جدة 🚘"
            await message.reply_text(reply)


# ============================================================
# 🌐 أوامر
# ============================================================
def get_bot(context):
    return context.application.bot_data["bot"]


async def chat_id_command(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    chat = update.effective_chat
    if chat.type in ("group", "supergroup"):
        text = (f"📌 <b>بيانات القروب</b>\n\n🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
                f"📋 النوع: <code>{chat.type}</code>\n"
                f"🏷 الاسم: {get_bot(context).html(chat.title) or 'بدون اسم'}")
    else:
        text = (f"📌 <b>بيانات المحادثة</b>\n\n🆔 Chat ID:\n<code>{chat.id}</code>\n\n"
                f"📋 النوع: <code>{chat.type}</code>")
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def start_command(update, context):
    user = update.effective_user
    get_bot(context).db.save_user(user)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 أنا عميل", callback_data=f"btn_customer:{user.id}"),
         InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"btn_driver:{user.id}")],
        [InlineKeyboardButton("⚠️ الشكاوي", callback_data="btn_complaints")],
    ])
    await update.effective_message.reply_text(WELCOME_TEXT, parse_mode=ParseMode.HTML,
                                              reply_markup=keyboard)


async def mybots_command(update, context):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return
    b = get_bot(context)
    await update.effective_message.reply_text(
        f"🤖 <b>حالة البوت</b>\n\n👤 المستخدم: {b.html(user.first_name)}\n"
        f"🆔 معرفك: <code>{user.id}</code>\n"
        f"📌 معرف القروب: <code>{GROUP_ID}</code>\n✅ البوت يعمل.",
        parse_mode=ParseMode.HTML)


async def error_handler(update, context):
    logger.error("❌ حدث خطأ:", exc_info=context.error)


# ============================================================
# 🚀 التشغيل
# ============================================================
def main():
    if not TOKEN:
        raise RuntimeError("❌ لم يتم العثور على BOT_TOKEN")
    bot = SmartRidesBot()
    application = Application.builder().token(TOKEN).build()
    application.bot_data["bot"] = bot

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("chatid", chat_id_command))
    application.add_handler(CommandHandler("mybots", mybots_command))
    application.add_handler(ChatMemberHandler(bot.handle_chat_member,
                                              ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS,
                                           bot.handle_new_members))
    application.add_handler(CallbackQueryHandler(bot.handle_take_trip, pattern=r"^take_trip:"))
    application.add_handler(CallbackQueryHandler(bot.handle_customer_contact,
                                                 pattern=r"^customer_contact:"))
    application.add_handler(CallbackQueryHandler(bot.handle_close_trip, pattern=r"^close_trip:"))
    application.add_handler(CallbackQueryHandler(bot.handle_callback_buttons, pattern=r"^btn_"))
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.CAPTION) & ~filters.COMMAND, bot.handle_message))
    application.add_error_handler(error_handler)

    logger.info("=" * 60)
    logger.info("🚀 تشغيل بوت مشاوير جدة - النسخة المصححة v2")
    logger.info("=" * 60)
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
