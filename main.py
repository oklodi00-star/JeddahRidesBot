import time
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ضع توكن البوت الخاص بك هنا
TOKEN = "YOUR_BOT_TOKEN_HERE"

# قاعدة بيانات مؤقتة لتخزين بيانات المستخدمين والرحلات النشطة
user_data = {}

def handle(msg):
    try:
        content_type, chat_type, chat_id = telepot.glance(msg)
        
        # 1. التعامل مع الرسائل النصية
        if content_type == 'text':
            text = msg['text']
            
            if text == '/start':
                user_data[chat_id] = {'step': 'MENU'}
                markup = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🚗 طلب مشوار فوري", callback_data='request_ride')],
                    [InlineKeyboardButton(text="💰 حاسبة الأسعار التقديرية", callback_data='calc_price')],
                    [InlineKeyboardButton(text="📋 رحلاتي السابقة", callback_data='my_rides')],
                    [InlineKeyboardButton(text="📞 خدمة العملاء والدعم", callback_data='support')]
                ])
                bot.sendMessage(
                    chat_id,
                    "أهلاً بك في **بوابتك لتنقلات مريحة في جدة** 🌴🚗\n"
                    "نحن نخدم جميع أحياء عروس البحر الأحمر على مدار الساعة.\n\n"
                    "اختر ما يناسبك من القائمة أدناه:",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )

            elif text == '/help':
                help_msg = (
                    "🛠 **دليل الاستخدام:**\n\n"
                    "/start - العودة للقائمة الرئيسية\n"
                    "/cancel - إلغاء الطلب الحالي\n"
                    "/help - عرض المساعدة\n\n"
                    "للبدء في حجز سيارة، اضغط على /start واقصد خيار طلب مشوار."
                )
                bot.sendMessage(chat_id, help_msg, parse_mode="Markdown")

            elif text == '/cancel':
                user_data[chat_id] = {'step': 'MENU'}
                bot.sendMessage(chat_id, "❌ تم إلغاء العملية الحالية. يمكنك البدء من جديد عبر /start")

            else:
                # التحقق من حالة المستخدم الخطواتية
                current_state = user_data.get(chat_id, {}).get('step')

                if current_state == 'WAITING_PICKUP':
                    user_data[chat_id]['pickup'] = text
                    user_data[chat_id]['step'] = 'WAITING_DESTINATION'
                    bot.sendMessage(chat_id, "📍 ممتاز. الآن أكتب **اسم الوجهة النهائية أو الحي المتجه إليه**:")

                elif current_state == 'WAITING_DESTINATION':
                    user_data[chat_id]['destination'] = text
                    user_data[chat_id]['step'] = 'SELECT_CAR_TYPE'
                    
                    # اختيار نوع السيارة
                    car_markup = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🚗 سيارة اقتصادية (صغيرة)", callback_data='car_eco')],
                        [InlineKeyboardButton(text="🚙 سيارة عائلية (SUV)", callback_data='car_family')],
                        [InlineKeyboardButton(text="✨ سيارة فاخرة VIP", callback_data='car_vip')]
                    ])
                    bot.sendMessage(
                        chat_id,
                        f"📍 **الانطلاق:** {user_data[chat_id]['pickup']}\n"
                        f"🏁 **الوصول:** {text}\n\n"
                        "اختر فئة السيارة المناسبة لرحلتك:",
                        reply_markup=car_markup,
                        parse_mode="Markdown"
                    )
                else:
                    bot.sendMessage(chat_id, "عذراً، لم أفهم رسالتك. استخدم /start للبدء من جديد.")

        # 2. التعامل مع الأزرار التفاعلية (Inline Keyboard)
        elif content_type == 'callback_query':
            query_id, chat_id, query_data = telepot.glance(msg, long=True)
            bot.answerCallbackQuery(query_id)

            if chat_id not in user_data:
                user_data[chat_id] = {'step': 'MENU'}

            if query_data == 'request_ride':
                user_data[chat_id]['step'] = 'WAITING_PICKUP'
                bot.sendMessage(chat_id, "📍 أرجو إرسال **موقع الانطلاق الحالي** (اسم الحي، الشارع، أو معلم مشهور في جدة):")

            elif query_data == 'calc_price':
                calc_text = (
                    "🧮 **حاسبة الأسعار التقديرية (داخل جدة):**\n\n"
                    "• المسافات القريبة (داخل نفس الحي): 25 - 35 ريال\n"
                    "• وسط جدة إلى الشمال (مثلاً التحلية إلى الروضة/المروة): 45 - 65 ريال\n"
                    "• جنوب جدة أو الكورنيش الشمالي: 60 - 90 ريال\n"
                    "• مطار الملك عبدالعزيز الدولي: يُحدد حسب موقع انطلاقك.\n\n"
                    "💡 الأسعار قابلة للتغيير البسيط بناءً على أوقات الذروة."
                )
                bot.sendMessage(chat_id, calc_text, parse_mode="Markdown")

            elif query_data == 'my_rides':
                bot.sendMessage(chat_id, "📋 ليس لديك رحلات مسجلة حالياً في هذا السجل المؤقت.")

            elif query_data == 'support':
                support_text = (
                    "📞 **فريق خدمة العملاء - جدة رایدز**\n\n"
                    "للاستفسارات العاجلة، المفقودات، أو الشكاوى:\n"
                    "• واتساب الدعم الفني: 966500000000+\n"
                    "• البريد الإلكتروني: support@jeddahrides.com\n\n"
                    "نحن بخدمتكم على مدار 24 ساعة."
                )
                bot.sendMessage(chat_id, support_text, parse_mode="Markdown")

            elif query_data.startswith('car_'):
                car_types = {
                    'car_eco': 'اقتصادية (صغيرة)',
                    'car_family': 'عائلية (SUV)',
                    'car_vip': 'فاخرة VIP'
                }
                selected_car = car_types.get(query_data, 'اقتصادية')
                ride_info = user_data.get(chat_id, {})
                
                pickup = ride_info.get('pickup', 'غير محدد')
                destination = ride_info.get('destination', 'غير محدد')

                # تأكيد نهائي للطلب
                confirmation_msg = (
                    "🎉 **تم تأكيد تفاصيل طلبك بنجاح!**\n\n"
                    f"📍 **من:** {pickup}\n"
                    f"🏁 **إلى:** {destination}\n"
                    f"🚙 **الفئة:** {selected_car}\n\n"
                    "⏳ **جاري الآن البحث عن أقرب كابتن متاح في جدة لتوصيلك...**\n"
                    "سيتواصل معك الكابتن قريباً."
                )
                bot.sendMessage(chat_id, confirmation_msg, parse_mode="Markdown")
                user_data[chat_id] = {'step': 'MENU'}

    except Exception as e:
        print(f"خطأ في المعالجة: {e}")

# تهيئة وتشغيل البوت
bot = telepot.Bot(TOKEN)
MessageLoop(bot, handle).run_as_thread()
print('Jeddah Rides Bot (Full Featured) يعمل الآن بنجاح...')

# حلقة الاستمرار لكي يظل السيرفر نشطاً على Render
while True:
    time.sleep(10)
