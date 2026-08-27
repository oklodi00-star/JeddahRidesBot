"""
🤖 بوت مشاوير جدة الذكي - مع بطاقات مزحة للكابتن
"""

import os
import re
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = "8881485708:AAFH_dJW08U-S5a25nfLePTbV3g1Odzjxrk"

GROUP_ID = -1001234567890
GROUP_NAME = "🚘 مشاوير جدة وضواحيها"
GROUP_LINK = "https://t.me/JeddahRides"

OWNER_ID = 952638746
ADMIN_USERNAME = "klodi500"
ADMIN_USERNAMES = ["klodi500"]
ADMIN_IDS = [952638746]

SAUDI_TZ = ZoneInfo("Asia/Riyadh")

DB_FILE = "smart_rides.db"

DRIVER_BADGE = "𓆩🚘𓆪 كابتن"
CUSTOMER_BADGE = "𓆩👤𓆪 عميل"

ENGAGEMENT_INTERVAL = 45 * 60

# ============================================================
# 📋 قانون القروب
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه مباشرة.

3️⃣ 🚕 الكابتن يضغط زر «أنا جاهز» تحت الطلب.

4️⃣ 💰 السعر والتفاهم بالخاص.

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🧠 كلمات ذكية
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "دوام", "مدرسة", "جامعة",
    "مشوار يومي", "توصيل يومي", "التزام", "مكان المنزل", "مكان الدوام",
    "لوكيشن", "عدد الايام", "عدد ايام الدوام",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني",
    "ابغى مشوار", "ابي مشوار", "احتاج توصيل",
    "من يوصلني", "فيه كابتن", "اوصلني", "ودني",
]

LOCATION_KEYWORDS = [
    "متواجد", "أنا في", "انا في", "موجود", "بالحي", "بحي",
    "الان في", "الحين في", "تواجد", "أنا بحي", "انا بحي"
]

# ============================================================
# 🎭 رسائل مزحة للكابتن
# ============================================================

DRIVER_JOKE_MESSAGES = [
    "😂 كابتن يطلب مشوار!",
    "🛠️ شكله تعطلت سيارته اليوم!",
    "🚕 الكابتن صار راكب اليوم! 😂",
    "😅 شكلها جات على الكابتن!",
    "😂 أووه! الكابتن يبي مشوار!",
    "🤣 الكابتن تعطلت سيارته!",
]

DRIVER_JOKE_ENDINGS = [
    "🚕 طيب يا كابتن، نوصلك؟ 😂",
    "😂 يلا بينا نودي الكابتن!",
    "🛣️ الله يعينك يا كابتن!",
    "😂 تصدق الكابتن يطلب توصيلة؟",
    "🚕 خل ننقذ الكابتن! 😂",
]

GREETINGS = [
    (["السلام عليكم", "سلام عليكم"], ["وعليكم السلام 🌹🚘", "وعليكم السلام يا هلا 👋"]),
    (["هلا", "مرحبا", "اهلا"], ["هلا وغلا 🌹", "يا هلا والله 👋"]),
    (["صباح الخير"], ["صباح النور ☀️🌹"]),
    (["مساء الخير"], ["مساء النور 🌙🌹"]),
]

CHAT_RESPONSES = [
    (["كيفك", "كيف حالك"], ["بخير 🌹", "تمام 😊"]),
    (["وش تسوي"], ["أنتظر مشوارك 😎🚘"]),
    (["تحبني"], ["أحبك ❤️"]),
    (["نكت", "قول نكتة"], ["مرة كابتن نسى العميل وراح 😂"]),
    (["شسمك"], ["اسمي بوت المشاوير 😎"]),
    (["طفشان", "ملل"], ["اطلب مشوار وتروق 🚘"]),
    (["احبك", "حبيبي"], ["حبيبي أنت 🌹"]),
    (["كم السعر"], ["💰 السعر بالتفاهم 🤝"]),
    (["بوت", "يا بوت"], ["نعم أنا هنا 🤖"]),
]

READY_MESSAGES = [
    "رافقتك السلامة يا كابتن 🚕🌹",
    "الله يوفقك 🤲🚘",
]

ENGAGEMENT_MESSAGES = [
    "🌅 <b>صباح الخير!</b>\n\nمن عنده مشوار؟ 🚕",
    "🚕 <b>الكباتن!</b>\n\nأعلنوا مواقعكم 📍",
]

BAD_WORDS = ["يا غبي", "يا حمار", "انقلع"]

# ============================================================
# 💾 قاعدة البيانات
# ============================================================

class Database:
    def __init__(self):
        self.db_file = DB_FILE
        self.init_db()
    
    def connect(self):
        con = sqlite3.connect(self.db_file)
        con.row_factory = sqlite3.Row
        return con
    
    def init_db(self):
        with self.connect() as con:
            cur = con.cursor()
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    role TEXT DEFAULT ''
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    customer_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ready_drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER,
                    driver_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trip_id, driver_id)
                )
            """)
            
            con.commit()
    
    def save_user(self, user):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO users (user_id, name, username)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    username = excluded.username
            """, (user.id, user.full_name, user.username or ""))
            con.commit()
    
    def set_role(self, user_id, role):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
            con.commit()
    
    def get_role(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else ""
    
    def get_user_role(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None
    
    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal"):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips 
                (message_id, customer_id, pickup, destination, trip_type)
                VALUES (?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type))
            con.commit()
            return cur.lastrowid
    
    def get_trip(self, trip_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id) VALUES (?, ?)", (trip_id, driver_id))
            con.commit()
            return cur.rowcount > 0
    
    def is_driver_ready(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM ready_drivers WHERE trip_id = ? AND driver_id = ?", (trip_id, driver_id))
            return cur.fetchone() is not None

# ============================================================
# 🤖 البوت الرئيسي
# ============================================================

class SmartRidesBot:
    def __init__(self):
        self.db = Database()
    
    def normalize_text(self, text):
        replacements = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}
        text = text.lower()
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def html(self, text):
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    def detect_trip_type(self, text):
        normalized = self.normalize_text(text)
        for word in MONTHLY_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "monthly"
        for word in NORMAL_TRIP_WORDS:
            if self.normalize_text(word) in normalized:
                return "normal"
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return "normal"
        return None
    
    def looks_like_trip(self, text):
        if self.detect_trip_type(text):
            return True
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return True
        trip_indicators = [
            "مكان المنزل", "مكان الدوام", "لوكيشن", "السعر",
            "التزام", "مشوار", "توصيل", "عدد الايام", "دوام",
        ]
        normalized = self.normalize_text(text)
        for word in trip_indicators:
            if self.normalize_text(word) in normalized:
                return True
        return False
    
    def extract_route(self, text):
        match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        home_match = re.search(r"مكان المنزل\s*[:：]\s*(.+)", text, re.IGNORECASE)
        work_match = re.search(r"مكان الدوام\s*[:：]\s*(.+)", text, re.IGNORECASE)
        if home_match and work_match:
            return home_match.group(1).strip(), work_match.group(1).strip()
        
        return None, None
    
    def detect_location(self, text):
        normalized = self.normalize_text(text)
        
        found_keyword = False
        for keyword in LOCATION_KEYWORDS:
            if self.normalize_text(keyword) in normalized:
                found_keyword = True
                break
        
        if not found_keyword:
            return None
        
        for keyword in LOCATION_KEYWORDS:
            normalized = normalized.replace(self.normalize_text(keyword), "")
        
        location = normalized.strip()
        location = re.sub(r'[،.؟!]', '', location).strip()
        
        if not location or len(location) < 2:
            return None
        
        return location
    
    def get_chat_response(self, text):
        normalized = self.normalize_text(text)
        for phrases, responses in CHAT_RESPONSES:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        return None
    
    def get_greeting(self, text):
        normalized = self.normalize_text
