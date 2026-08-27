"""
🤖 بوت مشاوير جدة الذكي
اللهجة السعودية - بدون إشعارات خاصة - يتذكر الأدوار نهائياً
"""

import os
import re
import random
import logging
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ============================================================
# ⚙️ الإعدادات
# ============================================================

TOKEN = os.environ.get("BOT_TOKEN", "8881485708:AAE_39hvBK9ST_syUT3s4_bcAVr8fll9mjY")
SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "smart_rides.db"

DRIVER_BADGE = "𓆩🚘𓆪 كابتن"
CUSTOMER_BADGE = "𓆩👤𓆪 عميل"

# ============================================================
# 🧠 الكلمات الذكية - باللهجة السعودية
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "دوام", "مدرسة", "جامعة",
    "مشوار يومي", "توصيل يومي", "التزام", "مكان البيت", "مكان الدوام",
    "لوكيشن", "عدد الايام", "اسبوعي", "أسبوعي", "عقد شهري", "اتفاق شهري",
    "مشاوير الدوام", "توصيل الدوام"
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "يوصلني", "يوديني",
    "ابغى مشوار", "ابي مشوار", "احتاج توصيل",
    "اوصلني", "ودني", "ابي اروح", "ابغى اروح",
    "محتاج مشوار", "محتاجة توصيل", "فيه كابتن"
]

LOCATION_KEYWORDS = [
    "متواجد", "أنا في", "انا في", "موجود", "بحي",
    "الان في", "الحين في", "تواجد", "موقعي", "مكاني",
    "انا عند", "أنا عند", "متواجدة", "موجودة"
]

GREETINGS = [
    (["السلام عليكم", "سلام عليكم"], ["وعليكم السلام 🌹", "وعليكم السلام يا هلا 👋"]),
    (["هلا", "مرحبا", "اهلا", "ياهلا"], ["هلا وغلا 🌹", "يا هلا والله 👋"]),
    (["صباح الخير", "صباح النور"], ["صباح النور ☀️🌹", "صباح الخير 🌹"]),
    (["مساء الخير", "مساء النور"], ["مساء النور 🌙🌹", "مساء الخير 🌹"]),
]

CHAT_RESPONSES = [
    (["كيفك", "كيف حالك", "وش اخبارك", "وشلونك"], ["بخير 🌹", "تمام 😊"]),
    (["وش تسوي", "وش قاعد تسوي"], ["أنتظر مشوارك 😎🚘"]),
    (["شسمك", "وش اسمك"], ["اسمي بوت المشاوير 😎"]),
    (["بوت", "يا بوت"], ["نعم أنا هنا 🤖"]),
    (["شكرا", "يعطيك العافية", "مشكور"], ["العفو 🌹", "تحت أمرك 😊"]),
    (["كم السعر", "بكم", "كم التكلفة"], ["💰 السعر بالتفاهم 🤝"]),
    (["ابي كابتن", "ابغى كابتن", "محتاج كابتن"], ["🚕 تفضل، اكتب مشوارك بالتفصيل"]),
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
                    role TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    trip_date TEXT,
                    trip_time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def is_driver(self, user_id):
        return self.get_role(user_id) == "driver"
    
    def create_trip(self, customer_id, pickup, destination, trip_type, trip_date, trip_time):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO trips (customer_id, pickup, destination, trip_type, trip_date, trip_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (customer_id, pickup, destination, trip_type, trip_date, trip_time))
            con.commit()
            return cur.lastrowid
    
    def get_user_trips(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT * FROM trips WHERE customer_id = ?
                ORDER BY created_at DESC LIMIT 5
            """, (user_id,))
            return [dict(row) for row in cur.fetchall()]

# ============================================================
# 🧠 معالج النصوص
# ============================================================

class NLP:
    def normalize(self, text):
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
        normalized = self.normalize(text)
        for word in MONTHLY_TRIP_WORDS:
            if self.normalize(word) in normalized:
                return "monthly"
        for word in NORMAL_TRIP_WORDS:
            if self.normalize(word) in normalized:
                return "normal"
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return "normal"
        return None
    
    def looks_like_trip(self, text):
        if self.detect_trip_type(text):
            return True
        if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
            return True
        return False
    
    def extract_route(self, text):
        match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None
    
    def extract_date_time(self, text):
        result = {'date': None, 'time': None}
        
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(ص|م|مساء|ظهر|عصر|مغرب|عشاء)?', text)
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(3) if time_match.group(3) else None
            if period and ('م' in period or 'مساء' in period or 'عصر' in period or 'مغرب' in period or 'عشاء' in period):
                if hour < 12:
                    hour += 12
            result['time'] = f"{hour:02d}:{time_match.group(2) if time_match.group(2) else '00'}"
        
        today = datetime.now(SAUDI_TZ)
        if 'بكرة' in text or 'غدا' in text or 'باجر' in text:
            result['date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            result['date'] = today.strftime('%Y-%m-%d')
        
        return result
    
    def detect_location(self, text):
        normalized = self.normalize(text)
        found = False
        for keyword in LOCATION_KEYWORDS:
            if self.normalize(keyword) in normalized:
                found = True
                break
        if not found:
            return None
        for keyword in LOCATION_KEYWORDS:
            normalized = normalized.replace(self.normalize(keyword), "")
        location = normalized.strip()
        location = re.sub(r'[،.؟!]', '', location).strip()
        if len(location) < 2:
            return None
        return location
    
    def get_greeting(self, text):
        normalized = self.normalize(text)
        for phrases, responses in GREETINGS:
            for phrase in phrases:
                if self.normalize(phrase) in normalized:
                    return random.choice(responses)
        return None
    
    def get_chat_response(self, text):
        normalized = self.normalize(text)
        for phrases, responses in CHAT_RESPONSES:
            for phrase in phrases:
                if self.normalize(phrase) in normalized:
                    return random.choice(responses)
        return None

# ============================================================
# 🤖 البوت الرئيسي
# ============================================================

db = Database()
nlp = NLP()

def get_badge(user_id):
    role = db.get_role(user_id)
    if role == "driver":
        return DRIVER_BADGE
    elif role == "customer":
        return CUSTOMER_BADGE
    return "𓆩❓𓆪 عضو"

def main_menu(user_id):
    role = db.get_role(user_id)
    keyboard = []
    
    if role == "driver":
        keyboard.append([
            InlineKeyboardButton("📍 الإعلان عن موقعي", callback_data="location"),
            InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
        ])
    elif role == "customer":
        keyboard.append([
            InlineKeyboardButton("🔍 طلب مشوار", callback_data="trip"),
            InlineKeyboardButton("📋 مشاويري", callback_data="my_trips")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("🚕 أنا كابتن", callback_data="reg_driver"),
            InlineKeyboardButton("👤 أنا عميل", callback_data="reg_customer")
        ])
    
    keyboard.append([
        InlineKeyboardButton("ℹ️ مساعدة", callback_data="help")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user = update.effective_user
    text = update.message.text.strip()
    user_id = user.id
    
    db.save_user(user)
    user_role = db.get_role(user_id)
    
    # فحص الكلمات السيئة
    normalized = nlp.normalize(text)
    for bad_word in BAD_WORDS:
        if nlp.normalize(bad_word) in normalized:
            await update.message.reply_text("⚠️ من فضلك التزم بالأدب")
            return
    
    # تحية
    greeting = nlp.get_greeting(text)
    if greeting:
        await update.message.reply_text(greeting)
        return
    
    # رد ذكي
    chat = nlp.get_chat_response(text)
    if chat:
        await update.message.reply_text(chat)
        return
    
    # طلب مشوار
    if nlp.looks_like_trip(text):
        trip_type = nlp.detect_trip_type(text)
        pickup, dest = nlp.extract_route(text)
        date_time = nlp.extract_date_time(text)
        
        db.create_trip(user_id, pickup or "غير محدد", dest or "غير محدد", trip_type or "normal", date_time['date'], date_time['time'])
        
        badge = get_badge(user_id)
        type_text = "🔄 شهري" if trip_type == "monthly" else "✨ عادي"
        
        trip_text = f"""
🚕 <b>مشوار جديد!</b>

{badge}: {nlp.html(user.full_name)}

📋 <b>النوع:</b> {type_text}
📍 <b>من:</b> {nlp.html(pickup or 'غير محدد')}
🎯 <b>إلى:</b> {nlp.html(dest or 'غير محدد')}
📅 <b>التاريخ:</b> {date_time['date'] or 'اليوم'}
⏰ <b>الوقت:</b> {date_time['time'] or 'غير محدد'}

🚕 <b>الكباتن اضغطوا "أنا جاهز"</b>
"""
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚕 أنا جاهز", callback_data=f"ready_{user_id}")
        ]])
        
        await update.message.reply_text(trip_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return
    
    # موقع كابتن
    location = nlp.detect_location(text)
    if location and user_role == "driver":
        await update.message.reply_text(
            f"{DRIVER_BADGE} <b>{nlp.html(user.full_name)}</b>\n"
            f"📍 <b>متواجد في:</b> {nlp.html(location)}",
            parse_mode=ParseMode.HTML
        )
        return
    
    # رد افتراضي
    if user_role:
        await update.message.reply_text(
            f"🤖 <b>أهلاً {nlp.html(user.full_name)}!</b>\n\n"
            "• اطلب مشوار: «ابي مشوار من X إلى Y»\n"
            "• كابتن أعلن موقعك: «متواجد في X»",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(user_id)
        )
    else:
        await update.message.reply_text(
            f"🤖 <b>أهلاً {nlp.html(user.full_name)}!</b>\n\n"
            "أنا بوت مشاوير جدة 🚕\n\n"
            "<b>اختر صفتك:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(user_id)
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    data = query.data
    
    if data == "reg_driver":
        db.set_role(user_id, "driver")
        await query.edit_message_text(
            f"✅ <b>تم تسجيلك ككابتن نهائياً!</b>\n\n"
            f"{DRIVER_BADGE}\n\n"
            f"لن نسألك مرة أخرى عن صفتك.\n\n"
            f"الآن يمكنك:\n"
            f"• الإعلان عن موقعك بقول «متواجد في...»\n"
            f"• الضغط على «أنا جاهز» تحت المشاوير",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(user_id)
        )
    
    elif data == "reg_customer":
        db.set_role(user_id, "customer")
        await query.edit_message_text(
            f"✅ <b>تم تسجيلك كعميل نهائياً!</b>\n\n"
            f"{CUSTOMER_BADGE}\n\n"
            f"لن نسألك مرة أخرى عن صفتك.\n\n"
            f"الآن يمكنك:\n"
            f"• طلب مشوار بقول «ابي مشوار من... إلى...»",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(user_id)
        )
    
    elif data.startswith("ready_"):
        await query.edit_message_text(
            f"✅ <b>{get_badge(user_id)} {nlp.html(user.full_name)} جاهز للمشوار!</b>",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "location":
        await query.edit_message_text(
            "📍 <b>اكتب موقعك الحالي:</b>\n\n"
            "مثال: «متواجد في الحمراء»",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "trip":
        await query.edit_message_text(
            "🚕 <b>اكتب تفاصيل مشوارك:</b>\n\n"
            "مثال: «ابي مشوار من الحمراء للسلامة بكرة 8 الصبح»\n\n"
            "للمشوار الشهري: «ابغى كابتن شهري للدوام»",
            parse_mode=ParseMode.HTML
        )
    
    elif data == "my_trips":
        trips = db.get_user_trips(user_id)
        if trips:
            text = "📋 <b>آخر مشاويرك:</b>\n\n"
            for t in trips:
                text += f"🔹 {t['pickup']} → {t['destination']}\n"
                text += f"   📅 {t['trip_date']} ⏰ {t['trip_time'] or 'غير محدد'}\n\n"
        else:
            text = "📭 <b>لا توجد مشاوير بعد</b>"
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu(user_id))
    
    elif data == "help":
        await query.edit_message_text(
            "ℹ️ <b>مساعدة البوت</b>\n\n"
            "<b>للكباتن:</b>\n"
            "• سجل مرة واحدة فقط\n"
            "• أعلن عن موقعك: «متواجد في...»\n"
            "• اضغط «أنا جاهز» تحت المشاوير\n\n"
            "<b>للعملاء:</b>\n"
            "• سجل مرة واحدة فقط\n"
            "• اطلب مشوار: «ابي مشوار من... إلى...»\n\n"
            "<b>أنواع المشاوير:</b>\n"
            "• عادي: مرة واحدة\n"
            "• شهري: يتكرر يومياً",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu(user_id)
        )

def main():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🤖 بوت مشاوير جدة يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
