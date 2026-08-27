import os
import re
import random
import logging
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8881485708:AAE_39hvBK9ST_syUT3s4_bcAVr8fll9mjY"

SAUDI_TZ = ZoneInfo("Asia/Riyadh")
DB_FILE = "bot_data.db"

MONTHLY_WORDS = ["شهري", "بالشهر", "كل يوم", "يوميا", "دوام", "مدرسة", "جامعة", "اسبوعي", "أسبوعي", "شهر", "مداوم"]
NORMAL_WORDS = ["مشوار", "توصيل", "يوصلني", "يوديني", "ابغى", "ابي", "احتاج", "اوصلني", "ودني", "خذني"]
PRESENCE_WORDS = ["متواجد", "موجود", "انا في", "أنا في", "انا عند", "متوفر", "مستعد", "جاهز"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                role TEXT DEFAULT ''
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                customer_id INTEGER,
                pickup TEXT,
                destination TEXT,
                trip_type TEXT DEFAULT 'normal'
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ready_drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id INTEGER,
                driver_id INTEGER,
                UNIQUE(trip_id, driver_id)
            )
        """)
        self.conn.commit()
    
    def save_user(self, user):
        self.cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, name, username)
            VALUES (?, ?, ?)
        """, (user.id, user.full_name, user.username or ""))
        self.conn.commit()
    
    def set_role(self, user_id, role):
        self.cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        self.conn.commit()
    
    def get_role(self, user_id):
        self.cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else ""
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type):
        self.cursor.execute("""
            INSERT INTO trips (message_id, customer_id, pickup, destination, trip_type)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, customer_id, pickup, destination, trip_type))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_trip(self, trip_id):
        self.cursor.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                "trip_id": row[0],
                "message_id": row[1],
                "customer_id": row[2],
                "pickup": row[3],
                "destination": row[4],
                "trip_type": row[5]
            }
        return None
    
    def add_ready_driver(self, trip_id, driver_id):
        try:
            self.cursor.execute("INSERT INTO ready_drivers (trip_id, driver_id) VALUES (?, ?)", (trip_id, driver_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

db = Database()

def normalize_text(text):
    replacements = {"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}
    text = text.lower()
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def detect_trip_type(text):
    normalized = normalize_text(text)
    for word in MONTHLY_WORDS:
        if normalize_text(word) in normalized:
            return "monthly"
    for word in NORMAL_WORDS:
        if normalize_text(word) in normalized:
            return "normal"
    if re.search(r"من\s+.+?\s+(?:الى|إلى|الي)\s+.+", text, re.IGNORECASE):
        return "normal"
    return None

def extract_route(text):
    match = re.search(r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        db.save_user(member)
        welcome_text = f"""
🌟 <b>يا هلا {member.full_name}!</b>

نورت القروب 🚘

👤 <b>عميل:</b> اكتب طلبك
🚕 <b>كابتن:</b> اكتب موقعك

✍️ اكتب «أنا كابتن» أو «أنا عميل»
"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👤 أنا عميل", callback_data=f"role_customer:{member.id}"),
                InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"role_driver:{member.id}"),
            ],
        ])
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def role_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("role_customer:"):
        role = "customer"
        role_text = "✅ <b>تم تسجيلك كعميل!</b>"
    elif data.startswith("role_driver:"):
        role = "driver"
        role_text = "✅ <b>تم تسجيلك ككابتن!</b>"
    else:
        return
    
    target_id = int(data.split(":")[1])
    db.save_user(query.from_user)
    db.set_role(target_id, role)
    await query.message.reply_text(role_text, parse_mode=ParseMode.HTML)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    
    if not message or not user or not message.text:
        return
    
    db.save_user(user)
    text = message.text
    normalized = normalize_text(text).strip()
    
    if normalized in ["انا كابتن", "انا سايق", "انا سواق", "كابتن"]:
        db.set_role(user.id, "driver")
        await message.reply_text("✅ <b>تم تسجيلك ككابتن!</b>\n\nاكتب موقعك:\nمثال: أنا متواجد في الفضيلة", parse_mode=ParseMode.HTML)
        return
    
    if normalized in ["انا عميل", "انا زبون", "عميل"]:
        db.set_role(user.id, "customer")
        await message.reply_text("✅ <b>تم تسجيلك كعميل!</b>\n\nاكتب مشوارك:\nمثال: من الفضيلة إلى الرغامة", parse_mode=ParseMode.HTML)
        return
    
    role = db.get_role(user.id)
    
    # تواجد الكابتن
    if any(word in normalized for word in [normalize_text(w) for w in PRESENCE_WORDS]):
        if role == "driver":
            location_match = re.search(r"(?:في|عند|بال)\s+(.+)", text)
            location = location_match.group(1).strip() if location_match else "غير محدد"
            
            presence_card = f"""
📍 <b>تم تسجيل تواجدك!</b>

👨‍✈️ <b>الكابتن:</b> {user.full_name}
🚕 <b>الموقع:</b> {location}
🕐 <b>الوقت:</b> {datetime.now(SAUDI_TZ).strftime('%H:%M')}

🙏 <b>الله يرزقك المشوار الطيب!</b>
"""
            await message.reply_text(presence_card, parse_mode=ParseMode.HTML)
            return
    
    # طلب مشوار
    trip_type = detect_trip_type(text)
    if trip_type:
        pickup, destination = extract_route(text)
        
        if not pickup or not destination:
            pickup = "غير محدد"
            destination = "غير محدد"
        
        trip_id = db.create_trip(message.message_id, user.id, pickup, destination, trip_type)
        
        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        
        trip_card = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>النوع:</b> {type_badge}
📍 <b>من:</b> {pickup}
🎯 <b>إلى:</b> {destination}

🚕 <b>للكباتن:</b> اضغط الزر بالأسفل
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚕 أنا جاهز للمشوار", callback_data=f"take_trip:{trip_id}:{user.id}")],
        ])
        
        await message.reply_text(trip_card, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        return

async def handle_take_trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    driver = query.from_user
    data = query.data.split(":")
    trip_id = int(data[1])
    customer_id = int(data[2])
    
    if driver.id == customer_id:
        await query.answer("😂 ما تقدر تأخذ مشوارك بنفسك!", show_alert=True)
        return
    
    db.save_user(driver)
    
    if not db.get_role(driver.id) == "driver":
        db.set_role(driver.id, "driver")
    
    added = db.add_ready_driver(trip_id, driver.id)
    
    if not added:
        await query.answer("✅ أنت مسجل جاهز لهذا المشوار!", show_alert=True)
        return
    
    trip = db.get_trip(trip_id)
    
    if not trip:
        await query.answer("⚠️ المشوار غير موجود!", show_alert=True)
        return
    
    type_badge = "🔄 شهري" if trip["trip_type"] == "monthly" else "🚗 عادي"
    
    card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {driver.full_name}

📋 <b>النوع:</b> {type_badge}
📍 <b>من:</b> {trip["pickup"]}
🎯 <b>إلى:</b> {trip["destination"]}

💰 <b>السعر:</b> بالتفاهم بالخاص
"""
    await query.message.reply_text(card_text, parse_mode=ParseMode.HTML)
    await query.answer("✅ تم تسجيلك للمشوار!", show_alert=True)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚘 <b>بوت المشاوير</b>\n\n"
        "👤 <b>عميل:</b> اكتب مشوارك\n"
        "🚕 <b>كابتن:</b> اكتب موقعك",
        parse_mode=ParseMode.HTML
    )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(role_selection, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(handle_take_trip, pattern="^take_trip:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ البوت يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
