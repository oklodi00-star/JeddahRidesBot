import os
import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

# =========================================================
# الإعدادات
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود. أضفه في GitHub Secrets."
    )

bot = telepot.Bot(TOKEN)

# تخزين مؤقت للطلبات
user_data = {}

# =========================================================
# القوائم
# =========================================================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚗 طلب مشوار فوري",
                callback_data="request_ride"
            )
        ],
        [
            InlineKeyboardButton(
                text="💰 حاسبة الأسعار",
                callback_data="calc_price"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 رحلاتي",
                callback_data="my_rides"
            )
        ],
        [
            InlineKeyboardButton(
                text="📞 خدمة العملاء",
                callback_data="support"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 قوانين القروب",
                callback_data="rules"
            )
        ]
    ])


def car_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🚗 اقتصادية",
                callback_data="car_eco"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚙 عائلية SUV",
                callback_data="car_family"
            )
        ],
        [
            InlineKeyboardButton(
                text="✨ VIP",
                callback_data="car_vip"
            )
        ]
    ])


# =========================================================
# الترحيب
# =========================================================

def send_start(chat_id):
    user_data[chat_id] = {
        "step": "MENU",
        "rides": []
    }

    text = (
        "🚘 *مشاوير جدة وضواحيها*\n\n"
        "أهلاً بك 👋\n"
        "بوابتك لتنظيم مشاويرك بسهولة وسرعة.\n\n"
        "📍 جدة • مكة • الطائف • وضواحيها\n"
        "🚗 خدمة المشاوير على مدار الساعة\n\n"
        "اختر من القائمة:"
    )

    bot.sendMessage(
        chat_id,
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )


# =========================================================
# معالجة الرسائل
# =========================================================

def handle(msg):
    try:
        content_type, chat_type, chat_id = telepot.glance(msg)

        # -------------------------------------------------
        # الرسائل النصية
        # -------------------------------------------------

        if content_type == "text":

            text = msg.get("text", "").strip()

            # /start
            if text == "/start":
                send_start(chat_id)
                return

            # /help
            if text == "/help":
                bot.sendMessage(
                    chat_id,
                    "🛠 *طريقة الاستخدام*\n\n"
                    "/start — القائمة الرئيسية\n"
                    "/cancel — إلغاء الطلب الحالي\n"
                    "/help — المساعدة\n\n"
                    "لطلب مشوار اضغط 🚗 طلب مشوار فوري.",
                    parse_mode="Markdown"
                )
                return

            # /cancel
            if text == "/cancel":
                user_data[chat_id] = {
                    "step": "MENU",
                    "rides": []
                }

                bot.sendMessage(
                    chat_id,
                    "❌ تم إلغاء العملية الحالية.\n\n"
                    "يمكنك البدء من جديد من القائمة الرئيسية.",
                    reply_markup=main_menu()
                )
                return

            # إنشاء بيانات المستخدم إذا لم تكن موجودة
            if chat_id not in user_data:
                user_data[chat_id] = {
                    "step": "MENU",
                    "rides": []
                }

            state = user_data[chat_id].get("step")

            # -------------------------------------------------
            # انتظار موقع الانطلاق
            # -------------------------------------------------

            if state == "WAITING_PICKUP":

                if len(text) < 2:
                    bot.sendMessage(
                        chat_id,
                        "⚠️ اكتب موقع الانطلاق بشكل أوضح."
                    )
                    return

                user_data[chat_id]["pickup"] = text
                user_data[chat_id]["step"] = "WAITING_DESTINATION"

                bot.sendMessage(
                    chat_id,
                    "📍 تم تسجيل موقع الانطلاق:\n"
                    f"*{text}*\n\n"
                    "🏁 الآن اكتب الوجهة النهائية:",
                    parse_mode="Markdown"
                )
                return

            # -------------------------------------------------
            # انتظار الوجهة
            # -------------------------------------------------

            if state == "WAITING_DESTINATION":

                if len(text) < 2:
                    bot.sendMessage(
                        chat_id,
                        "⚠️ اكتب اسم الوجهة بشكل أوضح."
                    )
                    return

                user_data[chat_id]["destination"] = text
                user_data[chat_id]["step"] = "SELECT_CAR"

                pickup = user_data[chat_id]["pickup"]

                bot.sendMessage(
                    chat_id,
                    "🚗 *تفاصيل المشوار*\n\n"
                    f"📍 من: *{pickup}*\n"
                    f"🏁 إلى: *{text}*\n\n"
                    "اختر فئة السيارة:",
                    reply_markup=car_menu(),
                    parse_mode="Markdown"
                )
                return

            # -------------------------------------------------
            # أي رسالة غير معروفة
            # -------------------------------------------------

            bot.sendMessage(
                chat_id,
                "👋 هلا بك.\n\n"
                "استخدم /start لفتح القائمة الرئيسية."
            )

        # -------------------------------------------------
        # الأزرار
        # -------------------------------------------------

        elif content_type == "callback_query":

            query_id, from_id, query_data = telepot.glance(
                msg,
                long=True
            )

            # تأكيد الضغط
            bot.answerCallbackQuery(query_id)

            # إنشاء بيانات المستخدم
            if from_id not in user_data:
                user_data[from_id] = {
                    "step": "MENU",
                    "rides": []
                }

            # -------------------------------------------------
            # طلب مشوار
            # -------------------------------------------------

            if query_data == "request_ride":

                user_data[from_id]["step"] = "WAITING_PICKUP"

                bot.sendMessage(
                    from_id,
                    "🚗 *طلب مشوار جديد*\n\n"
                    "📍 اكتب موقع الانطلاق.\n\n"
                    "مثال:\n"
                    "الصفا\n"
                    "أو\n"
                    "حي الزهراء"
                    "أو\n"
                    "مطار الملك عبدالعزيز",
                    parse_mode="Markdown"
                )

            # -------------------------------------------------
            # حاسبة الأسعار
            # -------------------------------------------------

            elif query_data == "calc_price":

                text = (
                    "💰 *حاسبة الأسعار التقديرية*\n\n"
                    "🚗 مشاوير داخل الأحياء:\n"
                    "25 — 40 ريال تقريباً\n\n"
                    "🚘 مشاوير متوسطة داخل جدة:\n"
                    "40 — 70 ريال تقريباً\n\n"
                    "🛣️ مشاوير بعيدة داخل جدة:\n"
                    "70 — 120 ريال تقريباً\n\n"
                    "✈️ المطار:\n"
                    "السعر يحدد حسب موقع الانطلاق.\n\n"
                    "⚠️ الأسعار تقديرية وقد تختلف حسب "
                    "المسافة والوقت والطلب."
                )

                bot.sendMessage(
                    from_id,
                    text,
                    reply_markup=main_menu(),
                    parse_mode="Markdown"
                )

            # -------------------------------------------------
            # الرحلات السابقة
            # -------------------------------------------------

            elif query_data == "my_rides":

                rides = user_data[from_id].get(
                    "rides",
                    []
                )

                if not rides:
                    bot.sendMessage(
                        from_id,
                        "📋 لا توجد رحلات مسجلة حتى الآن.",
                        reply_markup=main_menu()
                    )
                    return

                text = "📋 *رحلاتك السابقة*\n\n"

                for index, ride in enumerate(
                    rides[-10:],
                    start=1
                ):
                    text += (
                        f"{index}️⃣ "
                        f"{ride['pickup']} → "
                        f"{ride['destination']}\n"
                        f"🚙 {ride['car']}\n\n"
                    )

                bot.sendMessage(
                    from_id,
                    text,
                    reply_markup=main_menu(),
                    parse_mode="Markdown"
                )

            # -------------------------------------------------
            # الدعم
            # -------------------------------------------------

            elif query_data == "support":

                bot.sendMessage(
                    from_id,
                    "📞 *خدمة العملاء*\n\n"
                    "للاستفسارات أو المشاكل المتعلقة بالمشاوير، "
                    "تواصل مع إدارة القروب.\n\n"
                    "👤 الإدارة:\n"
                    "@klodi500",
                    reply_markup=main_menu(),
                    parse_mode="Markdown"
                )

            # -------------------------------------------------
            # القوانين
            # -------------------------------------------------

            elif query_data == "rules":

                rules = (
                    "📋 *قوانين مشاوير جدة وضواحيها*\n\n"
                    "1️⃣ القروب مخصص للمشاوير والنقل.\n\n"
                    "2️⃣ يمنع السب والإساءة.\n\n"
                    "3️⃣ يمنع نشر الروابط والإعلانات.\n\n"
                    "4️⃣ السعر والتفاهم بين العميل والكابتن.\n\n"
                    "5️⃣ يمنع إزعاج الأعضاء أو إرسال محتوى غير مناسب.\n\n"
                    "6️⃣ الالتزام بالمواعيد واحترام الطرف الآخر.\n\n"
                    "🚘 نتمنى للجميع مشاوير موفقة."
                )

                bot.sendMessage(
                    from_id,
                    rules,
                    reply_markup=main_menu(),
                    parse_mode="Markdown"
                )

            # -------------------------------------------------
            # اختيار السيارة
            # -------------------------------------------------

            elif query_data.startswith("car_"):

                car_types = {
                    "car_eco": "🚗 اقتصادية",
                    "car_family": "🚙 عائلية SUV",
                    "car_vip": "✨ VIP"
                }

                selected_car = car_types.get(
                    query_data,
                    "🚗 اقتصادية"
                )

                ride = user_data[from_id]

                pickup = ride.get(
                    "pickup",
                    "غير محدد"
                )

                destination = ride.get(
                    "destination",
                    "غير محدد"
                )

                ride_record = {
                    "pickup": pickup,
                    "destination": destination,
                    "car": selected_car
                }

                if "rides" not in user_data[from_id]:
                    user_data[from_id]["rides"] = []

                user_data[from_id]["rides"].append(
                    ride_record
                )

                user_data[from_id]["step"] = "MENU"

                bot.sendMessage(
                    from_id,
                    "✅ *تم تسجيل طلب المشوار*\n\n"
                    f"📍 من: *{pickup}*\n"
                    f"🏁 إلى: *{destination}*\n"
                    f"🚙 السيارة: *{selected_car}*\n\n"
                    "⏳ جاري البحث عن كابتن مناسب...\n\n"
                    "🚘 سيتم التواصل معك عند توفر كابتن.",
                    reply_markup=main_menu(),
                    parse_mode="Markdown"
                )

    except Exception as e:
        print(
            "حدث خطأ أثناء معالجة الرسالة:",
            repr(e)
        )


# =========================================================
# التشغيل
# =========================================================

def main():

    print("====================================")
    print("🚘 مشاوير جدة وضواحيها")
    print("🤖 البوت بدأ التشغيل")
    print("====================================")

    MessageLoop(
        bot,
        handle
    ).run_as_thread()

    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()