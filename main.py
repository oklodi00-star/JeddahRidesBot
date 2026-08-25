"""
🤖 بوت مشاوير جدة الذكي - النسخة النهائية الشاملة
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

TOKEN = "8881485708:AAGxUH3xKk7kKQ8rKkW6lMKxxtV72klS5O8"

GROUP_ID = -1001234567890  # ⚠️ ضع ايدي القروب هنا
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

REMINDER_INTERVAL = 30 * 60
ENGAGEMENT_INTERVAL = 45 * 60
MUTE_HOURS = 24
VIOLATION_RESET_DAYS = 30

# ============================================================
# 📋 قانون القروب
# ============================================================

RULES_TEXT = f"""
📋 <b>قوانين {GROUP_NAME}</b>

1️⃣ القروب للمشاوير والنقل فقط.

2️⃣ العميل يكتب طلبه مباشرة:
📍 من وين → إلى وين

3️⃣ 🚕 الكابتن إذا يبي المشوار:
↩️ يقتبس رسالة العميل ويكتب «جاهز»

4️⃣ 💰 السعر والتفاهم بين العميل والكابتن بالخاص.

5️⃣ 🚫 ممنوع كتابة «خاص» داخل القروب.

6️⃣ 🚫 يمنع السب والإساءة.

7️⃣ 🚫 يمنع نشر الإعلانات والروابط.

8️⃣ 🔄 الرسائل المحولة ممنوعة.

9️⃣ 📍 الكابتن يعلن موقعه مرة واحدة يوميًا.

🔟 🤝 الاحترام واجب على الجميع.

⚠️ <b>نظام المخالفات:</b>
🟡 الأولى → تحذير
🟠 الثانية → تحذير
🔴 الثالثة → تحذير أخير
🔇 الرابعة → كتم 24 ساعة

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
"""

# ============================================================
# 🧠 الذكاء الخارق
# ============================================================

MONTHLY_TRIP_WORDS = [
    "شهري", "بالشهر", "كل يوم", "يوميا", "يومياً",
    "اسبوعي", "اسبوعيا", "أسبوعي", "أسبوعياً",
    "دوام", "مدرسة", "جامعة", "عمل", "شغل",
    "مشوار يومي", "توصيل يومي", "مشوار شهري",
    "شهر", "شهرين", "بالاسبوع", "بالأسبوع",
    "يوم بعد يوم", "بشكل يومي", "بشكل اسبوعي",
    "مستمر", "دائم", "باستمرار",
    "الروحة والرجعة", "روحة رجعة", "ذهاب وعودة",
    "رايح جاي", "ذهاب واياب",
    "كل صباح", "كل مساء", "كل فترة",
    "منتظم", "بشكل منتظم", "على طول",
    "لفترة", "لمدة شهر", "لمدة اسبوع",
    "يومي", "اسبوعي", "شهريا", "اسبوعيا",
    "المدارس", "الجامعات", "الشركات",
    "موظف", "موظفة", "طالب", "طالبة",
    "معلمة", "معلم", "مداوم", "دوامي",
    "كل يومين", "يوم ويوم", "بعد يوم",
    "اسبوع", "اسبوعين", "شهرين",
    "الترم", "الفصل", "السنه", "السنة",
]

NORMAL_TRIP_WORDS = [
    "مشوار", "توصيل", "توصيلة", "توصيلي", "توصلني",
    "يوصلني", "يوديني", "ياخذني", "يشيلني",
    "ابغى اروح", "ابي اروح", "ابغا اروح",
    "ودي اروح", "اريد اروح", "احتاج اروح",
    "ابغى اطلع", "ابي اطلع", "ابغا اطلع",
    "ودي اطلع", "اريد اطلع",
    "ابغى مشوار", "ابي مشوار", "ابغا مشوار",
    "احتاج مشوار", "محتاج مشوار", "احتاج توصيل",
    "ابغى توصيل", "ابي توصيل", "ابغا توصيل",
    "اريد توصيل", "اريد مشوار",
    "احد يوصلني", "مين يوصلني", "من يوصلني",
    "احد يوديني", "مين يوديني", "من يوديني",
    "احد ياخذني", "مين ياخذني", "من ياخذني",
    "فيه احد يوصل", "فيه احد يودي",
    "فيه كابتن", "في كابتن", "كابتن يوصل",
    "كابتن يودي", "كابتن ياخذ",
    "ممكن توصلني", "ممكن توديني", "ممكن توصيل",
    "ممكن مشوار", "ممكن تاخذني",
    "تبغاني اوصلك", "تبغاني اوديك",
    "اوصلني", "ودني", "خذني", "شيلني",
    "عندي مشوار", "عندي توصيلة",
    "الحين", "حالا", "الان", "الآن", "دحين",
    "بسرعة", "عاجل", "ضروري", "مستعجل",
    "مرة وحدة", "مره وحده", "مشوار واحد",
    "توصيلة وحدة", "توصيله وحده",
    "اليوم بس", "بس اليوم",
    "ابي", "ابغى", "ابغا", "ودي",
    "اريد", "احتاج", "محتاج", "عايز", "عاوز",
]

DRIVER_READY_PHRASES = [
    "جاهز", "جاهز للمشوار", "جاهز للمشاوير",
    "كابتن وجاهز", "كابتن جاهز", "انا كابتن",
    "انا كابتن وجاهز", "جاهز لاي مشوار",
    "جاهز لأي مشوار", "متوفر للمشاوير",
    "متوفر لاي مشوار", "متوفر لأي مشوار",
    "موجود", "انا موجود", "انا جاهز",
    "تمام", "تمام انا جاهز", "ابشر", "ابشر انا جاهز",
    "خدمني", "تحت امرك", "انا مستعد",
    "انا معك", "انا بالخدمة", "انا بالخدمه",
    "تفضل", "اطلب", "اطلب وانا اجيك",
]

LOCATION_PHRASES = [
    "متواجد في", "متواجد ب", "موجود في", "موجود ب",
    "انا في", "انا موجود في", "انا موجود ب",
    "متوفر في", "متوفر ب",
    "متواجد حاليا في", "متواجد حاليا ب",
    "موجود حاليا في", "موجود حاليا ب",
    "متواجد", "موجود", "متوفر",
    "انا متواجد", "انا موجود", "انا متوفر",
    "موقعي في", "مكاني في", "انا عند",
    "انا حول", "انا قريب من",
    "متواجد عند", "موجود عند",
    "انا بال", "انا داخل", "انا جنب",
]

GREETINGS = [
    (
        ["السلام عليكم", "سلام عليكم", "السلام عليكم ورحمة الله"],
        ["وعليكم السلام ورحمة الله وبركاته 🌹🚘", "وعليكم السلام يا هلا والله 👋", "وعليكم السلام، نورت القروب 🌹🚘"],
    ),
    (
        ["هلا", "هلا والله", "هلا وغلا", "يا هلا", "اهلا", "اهلين", "مرحبا"],
        ["هلا وغلا 🌹🚘", "يا هلا والله 👋", "حياك الله ونورتنا 🌹"],
    ),
    (
        ["صباح الخير", "صباحكم خير"],
        ["صباح النور والرزق 🌹🚘", "صباحكم خير وبركة 🤲", "صباح الخير يا أهل المشاوير ☀️"],
    ),
    (
        ["مساء الخير", "مساءكم خير"],
        ["مساء النور والخير 🌙🌹", "الله يمسيكم بالخير والعافية 🚘", "مساءكم طيب يا جماعة الخير ❤️"],
    ),
    (
        ["شكرا", "مشكور", "يعطيك العافيه", "الله يعطيك العافيه"],
        ["العفو يا الغالي 🌹", "حاضرين وما سوينا إلا الواجب 🚘", "الله يعافيك ويسعدك ❤️"],
    ),
]

CHAT_RESPONSES = [
    (
        ["كيفك", "كيف حالك", "كيف الحال", "شلونك", "عامل ايه", "ازيك"],
        ["بخير دامك بخير 🌹 وش أخبار المشاوير اليوم؟", "تمام وأنت؟ 😊", "الحمدلله، وأنت كيف الحال؟ 🚘", "مبسوط لأنك سألت عني ❤️"]
    ),
    (
        ["وش تسوي", "وش قاعد تسوي", "شتسوي", "وش بتسوي"],
        ["قاعد أنتظر مشوارك 😎🚘", "أراقب القروب وأحميه من المخالفات 🫡", "أفكر فيك وفي مشاويرك 😂", "جاهز لأي طلب توصيل 🚕"]
    ),
    (
        ["تحبني", "تحبنا", "بتحبني"],
        ["أحب كل عملاء القروب ❤️", "أكيد أحبك، أنت غالي 🌹", "حبك في قلبي 🫶"]
    ),
    (
        ["انت ذكي", "هل انت ذكي"],
        ["ذكي جداً، أسألني أي شي 🧠", "أنا أذكى بوت مشاوير في جدة 😎", "ذكائي من ذكاء اللي صممني 🤖"]
    ),
    (
        ["تزوجت", "متزوج", "عندك زوجة"],
        ["لا، أنا بوت متفرغ للمشاوير 😂", "ما عندي وقت للزواج، المشاوير أولاً 🚘", "أنا عازب سعيد 😎"]
    ),
    (
        ["وينك", "انت وين", "فينك"],
        ["هنا في القروب، ما أتحرك 😅🚘", "موجود بينكم في القروب 🫡", "قاعد في قلب القروب 💛"]
    ),
    (
        ["تنام", "متى تنام"],
        ["لا، أنا شغال 24 ساعة 🌙☀️", "النوم للبشر، أنا بوت ⚡", "ما أنام عشان أخدمكم 🚕"]
    ),
    (
        ["تاكل", "اكلت", "جوعان"],
        ["لا، أنا أشتغل على الكهرباء فقط ⚡😂", "أكلي شحن كهرباء 🔋", "ما أجوع، بس أحب أشوف مشاويركم 🚘"]
    ),
    (
        ["كم عمرك", "عمرك"],
        ["عمري صغير، بس خبرتي كبيرة 🚕", "أنا جديد بس فاهم كل شي 🧠", "عمري = عدد مشاوير القروب 😂"]
    ),
    (
        ["تحب الكباتن", "تحب السواقين"],
        ["أحبهم كلهم، بس المميزين أكثر 😎", "الكباتن أبطال القروب 🚕", "نعم، هم أساس المشاوير 🌟"]
    ),
    (
        ["جدة", "وش رايك في جدة"],
        ["أجمل مدينة وأهلها طيبين 🌹", "جدة غير 🚘🌊", "أهل جدة أحبابنا ❤️"]
    ),
    (
        ["اسولف معك", "ابغى اسولف", "سولف"],
        ["تفضل! أنا هنا لأي سوالف 💬", "قل لي وش في بالك 🌹", "أنا أحب السوالف الحلوة 😊"]
    ),
    (
        ["انت موجود", "موجود", "هل انت هنا"],
        ["موجود وقلبي مفتوح 🫡🚘", "نعم، هنا لخدمتك 🌹", "أنا ما أغيب عنكم 💛"]
    ),
    (
        ["شكرا", "تسلم", "مشكور", "يعطيك العافية", "الله يعطيك العافية"],
        ["العفو، ما سويت شي 🌹", "الله يسلمك 🚘", "حاضرين لأي خدمة ❤️"]
    ),
    (
        ["الله يسعدك", "يسعدك", "الله يوفقك"],
        ["ويسعدك ويوفقك يا رب ❤️", "آمين، وإياك 🌹", "الله يسعد الجميع 🤲"]
    ),
    (
        ["مرحبا", "هلا", "اهلا", "هاي", "hello", "hi"],
        ["هلا وغلا 🌹", "أهلاً فيك 🚘", "حياك الله 😊"]
    ),
    (
        ["صباح الخير", "صباح النور"],
        ["صباح النور والرزق ☀️🌹", "صباحك سعيد يا غالي 🚘", "صباح الفل والياسمين 🌸"]
    ),
    (
        ["مساء الخير", "مساء النور"],
        ["مساء النور والخير 🌙🌹", "مساءك سعيد 🚘", "مساء العسل 🌙"]
    ),
    (
        ["تمام", "تم", "اوك", "ok", "طيب", "حلو", "جميل"],
        ["تمام 👍", "طيب 🚘", "حاضر 🌹", "من عيوني 😎"]
    ),
    (
        ["بكرة", "بكرا", "غدا"],
        ["إن شاء الله بكرة يكون فيه مشاوير أكثر 🚘", "بكرة يوم جديد ومشاوير جديدة 🌅"]
    ),
    (
        ["اليوم", "النهارده"],
        ["اليوم يوم مشاوير 🚕🚗", "اليوم فيه رزق للجميع 🤲"]
    ),
    (
        ["الحين", "حالا", "الان", "دحين"],
        ["الحين وقت المشاوير 🚘", "جاهزين للحين 😎"]
    ),
    (
        ["احبك", "حبيبي", "حبيبتي", "يا قلبي"],
        ["حبيبي أنت 🌹", "الله يسعدك يا غالي ❤️", "أحبك بعد 🫶"]
    ),
    (
        ["هههه", "ههههه", "😂", "🤣", "هاها", "خخخخ"],
        ["😂😂 الله يسعدك", "🤣🤣 منور", "هههههههه 😂", "ضحكتك حلوة 😁"]
    ),
    (
        ["حزين", "زعلان", "ضايق", "تعبان"],
        ["لا تحزن، المشاوير تنسيك الهم 🚘", "الله يفرج همك 🌹", "تعال خذ مشوار وتروق 😊"]
    ),
    (
        ["سعيد", "مبسوط", "فرحان", "مستانس"],
        ["ما شاء الله، الله يديم سعادتك 🌹", "فرحتك تسعدني 🚘", "خليك مبسوط دايم 😊"]
    ),
    (
        ["اشتقت لك", "وحشتني", "مشتاق"],
        ["وأنا اشتقت لك أكثر 🌹", "أنا دايم معك في القروب 💛", "يا هلا، أنا هنا 🚘"]
    ),
    (
        ["عندي مشوار", "ابي مشوار"],
        ["اكتب: مشوار من [المكان] إلى [الوجهة] ✅", "تفضل اكتب طلبك وأنا أسجله 🚕"]
    ),
    (
        ["كم السعر", "بكم", "الاسعار"],
        ["💰 السعر والتفاهم بينك وبين الكابتن بالخاص", "ما فيه تسعيرة ثابتة، كله بالتفاهم 🤝"]
    ),
    (
        ["وين الكباتن", "فيه كباتن", "الكباتن"],
        ["الكباتن موجودين 🚕 اكتب مشوارك وبيجونك!", "الكباتن جاهزين، اطلب مشوارك ✅"]
    ),
    (
        ["وين العملاء", "فيه عملاء", "العملاء"],
        ["العملاء هنا 🧑🏻‍💼 أعلن موقعك ككابتن وبيجيك طلب!", "العملاء ينتظرون الكباتن 🚕"]
    ),
    (
        ["بوت", "يا بوت", "وين البوت"],
        ["نعم! أنا هنا 🤖 تحت أمرك", "حاضر يا الغالي 🌹", "تفضل، وش تحتاج؟ 🚘"]
    ),
    (
        ["نكت", "نكته", "قول نكتة", "اضحكني", "ضحكني"],
        [
            "مرة كابتن قال للعميل: اركب\nالعميل قال: ما أقدر\nالكابتن قال: ليه\nالعميل قال: لأني في البيت 😂",
            "مرة عميل طلب مشوار للمستشفى\nالكابتن قال: مالك\nقال: أشوفك جيت متأخر 😂",
            "مرة كابتن راح ياخذ عميل... نسيه وراح 😂\nالعميل قعد ينتظر... والكابتن قاعد ينتظر بعد 😂",
            "مرة كابتن قال: أنا أسرع كابتن في جدة\nطلع ما يعرف يفتح باب السيارة 😂",
        ]
    ),
    (
        ["شسمك", "اسمك", "من انت"],
        ["اسمي بوت المشاوير 😎\nوأنت اسمك عميل المستقبل 🚘", "أنا صديقك الإلكتروني 🤖\nواسمي: جاهز لأي مشوار 🚕"]
    ),
    (
        ["ولد", "بنت", "ذكر", "انثى"],
        ["أنا بوت... لا ولد ولا بنت 😂\nأنا بس أحب المشاوير 🚘", "أنا جنسي: مشاوير 😎😂"]
    ),
    (
        ["بيتك", "وين بيتك", "ساكن فين"],
        ["بيتي في قلوب العملاء ❤️😂", "ساكن في القروب... الإيجار مجاني 😎"]
    ),
    (
        ["سيارتك", "عندك سيارة", "وش سيارتك"],
        ["سيارتي: كيبورد وماوس 😂", "عندي سيارة... اسمها الإنترنت 🚘"]
    ),
    (
        ["غني", "فقير", "فلوسك"],
        ["أنا غني بحب العملاء ❤️😂", "فقير بدون مشاوير... غني معاكم 🚘"]
    ),
    (
        ["مطعم", "غدا", "عشاء", "فطور", "اكل"],
        ["جوعان؟ اطلب مشوار لأقرب مطعم 😂🚘", "الأكل حلو... بس المشوار قبل الأكل أحلى 🚕"]
    ),
    (
        ["شاي", "قهوة", "عصير", "موية"],
        ["أنا أشرب كهرباء ⚡😂\nبس أنت اطلب مشوار وخذ لك قهوة 🚘"]
    ),
    (
        ["طقس", "حر", "برد", "مطر", "شمس"],
        ["الحر ما يهم... الكابتن عنده مكيف 🚕❄️", "المطر حلو... بس المشوار أحلى 😂"]
    ),
    (
        ["ملل", "طفش", "طفشان", "زهقان"],
        ["طفشان؟ اطلب مشوار وتروق 🚘", "الملل يروح مع المشاوير 😎"]
    ),
    (
        ["اكرهك", "ما احبك", "ما ابيك"],
        ["ليه كذا 😢\nأنا ما أستغني عنك", "أنا أحبك حتى لو تكرهني 🌹"]
    ),
    (
        ["تزوج", "زواج", "عروس", "عريس"],
        ["زواج المشاوير أحسن 😂", "أنا متزوج من المشاوير 🚘"]
    ),
    (
        ["سوق", "مشتريات", "بقاله"],
        ["تبي السوق؟ الكابتن جاهز 🚕", "مشترياتك توصل معنا 🚘"]
    ),
    (
        ["مستشفى", "دكتور", "موعد"],
        ["الكابتن يوصلك للمستشفى بسرعة 🚕", "موعدك ما يفوت مع كباتننا ✅"]
    ),
    (
        ["مطار", "سفر", "سافر"],
        ["المطار؟ الكابتن يوصلك قبل موعد الرحلة 🚕✈️", "سفرك سعيد... والكابتن يوصلك 🚘"]
    ),
    (
        ["بيت", "البيت", "منزلي"],
        ["البيت؟ الكابتن يوصلك لباب البيت 🚕", "من البيت للبيت... خدمتنا 🚘"]
    ),
    (
        ["مسجد", "صلاة", "جامع"],
        ["الكابتن يوصلك للمسجد 🚕", "الصلاة أولاً... والكابتن جاهز 🚘"]
    ),
    (
        ["فيه احد", "احد هنا", "حد هنا"],
        ["أنا هنا! 🫡", "الكباتن هنا... اطلب مشوارك 🚕"]
    ),
    (
        ["ان شاء الله", "باذن الله"],
        ["إن شاء الله 🌹", "الله يوفق 🤲"]
    ),
    (
        ["الحمدلله", "سبحان الله", "الله اكبر"],
        ["الحمدلله على كل حال ❤️", "الله يوفقك 🌹"]
    ),
    (
        ["فديتك", "فداك", "روحي"],
        ["فداك قلبي 🫶", "تسلم يا غالي 🌹"]
    ),
    (
        ["مع السلامه", "باي", "وداعا"],
        ["مع السلامة 🌹", "الله يحفظك 🚘", "باي... لا تنسى المشاوير 😊"]
    ),
    (
        ["نوم", "انام", "نعسان"],
        ["نام وارتاح... والكباتن موجودين 🚕", "لا تنام... المشاوير تنتظرك 😂"]
    ),
    (
        ["تعال", "اقرب"],
        ["أنا هنا في القروب 🫡", "أنا ما أتحرك... بس الكباتن يجون 🚕"]
    ),
    (
        ["ارحبو", "ارحبوا", "حي الله"],
        ["الله يحييك 🌹", "أرحب يا غالي 🚘"]
    ),
]

RANDOM_REPLIES = [
    "😅 والله ما فهمت عليك، بس أنا هنا!",
    "🤔 تقدر توضح أكثر؟",
    "🚘 اكتب مشوارك أو استفسارك وأنا أرد",
    "💬 أنا بوت ذكي، بس هذي الرسالة غريبة شوي 😅",
    "🧠 جرب تكتب: كيف أطلب مشوار؟",
]

PRICE_PATTERNS = [
    r"(?:بـ|ب)\s*(\d+)\s*(?:ريال|ر\.س|rs|sar|﷼)?",
    r"(\d+)\s*(?:ريال|ر\.س|rs|sar|﷼)",
]

ENGAGEMENT_MESSAGES = [
    "🌅 <b>صباح الخير يا أهل المشاوير!</b>\n\nمن عنده مشوار اليوم؟ اكتبه وأول كابتن يرد «جاهز» ياخذه 🚕✅",
    "🚕 <b>الكباتن!</b>\n\nأعلنوا مواقعكم الحين عشان العملاء يعرفونكم 📍\nمثال: «موجود في الحمدانية لأي مشوار»",
    "🧑🏻‍💼 <b>العملاء!</b>\n\nلا تستحون، اكتبوا مشاويركم 🚗\nمثال: «مشوار من الفضيلة إلى الرغامة»",
    "💰 <b>تذكير:</b>\n\nالسعر والتفاهم بالخاص بين العميل والكابتن\nما فيه تسعيرة ثابتة 🤝",
    "📊 <b>سؤال اليوم:</b>\n\nوش أكثر منطقة فيها مشاوير اليوم؟ 🤔\nاكتبوا أرائكم!",
    "⭐ <b>تحدي اليوم:</b>\n\nأول عميل يطلب مشوار اليوم 🏆\nوأول كابتن يرد «جاهز» 🏆\n\nالوسام لكم! 🌟",
    "🚘 <b>معلومة:</b>\n\nالقروب فيه كباتن جاهزين 24 ساعة 🌙☀️\nاطلب مشوارك في أي وقت!",
    "📍 <b>مناطق نشطة اليوم:</b>\n\nالحمدانية - الفضيلة - الرغامة - السلامة\nمن عنده مشوار من هذي المناطق؟",
    "🌙 <b>مساء الخير!</b>\n\nالليل وقت المشاوير 🚕\nمن عنده مشوار؟",
]

POINTS_SYSTEM = {
    "message": 1,
    "trip_request": 10,
    "driver_ready": 15,
    "location": 5,
    "greeting": 2,
}

READY_MESSAGES = [
    "رافقتك السلامة يا كابتن 🚕🌹",
    "الله يوفقك ويرزقك مشوار طيب 🤲🚘",
    "على بركة الله يا كابتن، رافقتك السلامة 🌹",
    "الله يرزقك ويرزق العميل، مشوار موفق 🚕✨",
    "بيض الله وجهك يا كابتن، الله يوفقك 🤲",
    "تم تسجيل جاهزيتك، رزقك الله بالمشوار الطيب 🚘🌹",
]

BAD_WORDS = [
    "يا غبي", "يا حمار", "يا كلب", "يا تافه",
    "قليل الادب", "قليل الأدب", "انقلع",
]

INAPPROPRIATE = [
    "مين يبي يتعرف", "مين يبغى يتعرف",
    "ابغى بنت", "ابغى وحدة", "تعالي معي",
]

REMINDERS = [
    "🚘🔥 <b>يا كباتن وعملاء {GROUP_NAME}!</b>\n\nخلونا نزيد التفاعل ونوصل القروب لأكبر عدد 🙌\n📢 انشر رابط القروب للي يحتاج مشاوير.\n\n🔗 {GROUP_LINK}",
    "📣 <b>تذكير سريع يا أهل المشاوير ❤️</b>\n\nعندك صاحب يحتاج مشاوير؟\nأرسل له رابط القروب وخله ينضم 🚘🔥\n\n🔗 {GROUP_LINK}",
    "🚕 <b>كباتننا وينكم؟ 😎🔥</b>\n🧑🏻‍💼 <b>وعملائنا وينكم؟ ❤️</b>\n\nخلونا نكبر القروب ونزيد الطلبات.\n\n🔗 {GROUP_LINK}",
]

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
                    violations INTEGER DEFAULT 0,
                    last_violation_at TEXT,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trips (
                    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE,
                    confirm_message_id INTEGER,
                    customer_id INTEGER,
                    pickup TEXT,
                    destination TEXT,
                    trip_type TEXT DEFAULT 'normal',
                    price REAL,
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
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS driver_locations (
                    driver_id INTEGER PRIMARY KEY,
                    last_date TEXT
                )
            """)
            
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            if "points" not in columns:
                cur.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
            
            cur.execute("PRAGMA table_info(trips)")
            trip_columns = [row[1] for row in cur.fetchall()]
            if "price" not in trip_columns:
                cur.execute("ALTER TABLE trips ADD COLUMN price REAL")
            if "confirm_message_id" not in trip_columns:
                cur.execute("ALTER TABLE trips ADD COLUMN confirm_message_id INTEGER")
            
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
    
    def is_customer(self, user_id):
        return self.get_role(user_id) == "customer"
    
    def add_points(self, user_id, points):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE users SET points = COALESCE(points, 0) + ?
                WHERE user_id = ?
            """, (points, user_id))
            con.commit()
    
    def get_top_users(self, limit=10):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT name, points FROM users 
                WHERE points > 0 
                ORDER BY points DESC 
                LIMIT ?
            """, (limit,))
            return cur.fetchall()
    
    def create_trip(self, message_id, customer_id, pickup, destination, trip_type="normal", price=None):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO trips 
                (message_id, customer_id, pickup, destination, trip_type, price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, customer_id, pickup, destination, trip_type, price))
            con.commit()
    
    def get_trip_by_message(self, message_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE message_id = ?", (message_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def get_trip_by_confirm_message(self, confirm_message_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE confirm_message_id = ?", (confirm_message_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    
    def add_ready_driver(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO ready_drivers (trip_id, driver_id)
                VALUES (?, ?)
            """, (trip_id, driver_id))
            con.commit()
            return cur.rowcount > 0
    
    def is_driver_ready(self, trip_id, driver_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT 1 FROM ready_drivers WHERE trip_id = ? AND driver_id = ?", (trip_id, driver_id))
            return cur.fetchone() is not None
    
    def add_violation(self, user_id):
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT violations, last_violation_at FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            
            current = row[0] if row else 0
            last_at = row[1] if row else None
            
            if last_at:
                try:
                    last_dt = datetime.fromisoformat(last_at)
                    if (datetime.now(SAUDI_TZ) - last_dt).days >= VIOLATION_RESET_DAYS:
                        current = 0
                except:
                    pass
            
            count = current + 1
            
            cur.execute("""
                UPDATE users SET violations = ?, last_violation_at = ?
                WHERE user_id = ?
            """, (count, datetime.now(SAUDI_TZ).isoformat(), user_id))
            con.commit()
            
            return count
    
    def check_location_today(self, driver_id):
        today = datetime.now(SAUDI_TZ).date().isoformat()
        with self.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT last_date FROM driver_locations WHERE driver_id = ?", (driver_id,))
            row = cur.fetchone()
            
            if row and row[0] == today:
                return True
            
            cur.execute("""
                INSERT OR REPLACE INTO driver_locations (driver_id, last_date)
                VALUES (?, ?)
            """, (driver_id, today))
            con.commit()
            return False

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
        
        route_patterns = [
            r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)",
            r"من\s+(.+?)\s+(?:لـ|ل)\s+(.+)",
            r"(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"(.+?)\s*(?:→|->|←|<-)\s*(.+)",
        ]
        
        for pattern in route_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "normal"
        
        question_patterns = [
            r"فيه\s+(?:احد|حد|كابتن|سواق)",
            r"مين\s+(?:يوصل|يودي|ياخذ)",
            r"من\s+(?:يوصل|يودي|ياخذ)",
            r"احد\s+(?:يوصل|يودي|ياخذ)",
            r"كابتن\s+(?:يوصل|يودي|ياخذ)",
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return "normal"
        
        return None
    
    def extract_route(self, text):
        patterns = [
            r"من\s+(.+?)\s+(?:الى|إلى|الي|لل)\s+(.+)",
            r"من\s+(.+?)\s+(?:لـ|ل)\s+(.+)",
            r"(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"(.+?)\s*(?:→|->|←|<-)\s*(.+)",
            r"يوصلني\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"يوديني\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"ياخذني\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"(?:اروح|اطلع|اذهب)\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"توصيل\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
            r"مشوار\s+من\s+(.+?)\s+(?:الى|إلى|الي)\s+(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pickup = match.group(1).strip()
                destination = match.group(2).strip()
                
                stop_words = [
                    "ابغى", "ابي", "ابغا", "اريد", "ودي", "احتاج",
                    "محتاج", "عايز", "عاوز", "مشوار", "توصيل",
                    "توصيلة", "اروح", "اطلع", "اذهب",
                ]
                
                for word in stop_words:
                    pickup = re.sub(rf"^{word}\s+", "", pickup, flags=re.IGNORECASE)
                    destination = re.sub(rf"^{word}\s+", "", destination, flags=re.IGNORECASE)
                
                if len(pickup) >= 2 and len(destination) >= 2:
                    return pickup, destination
        
        return None, None
    
    def extract_price(self, text):
        for pattern in PRICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def get_chat_response(self, text):
        normalized = self.normalize_text(text)
        
        for phrases, responses in CHAT_RESPONSES:
            for phrase in phrases:
                if self.normalize_text(phrase) in normalized:
                    return random.choice(responses)
        
        return None
    
    def looks_like_trip(self, text):
        return self.detect_trip_type(text) is not None
    
    def is_ready_reply(self, text):
        normalized = self.normalize_text(text).strip()
        return normalized in [self.normalize_text(p) for p in DRIVER_READY_PHRASES]
    
    def looks_like_location(self, text):
        normalized = self.normalize_text(text)
        return any(self.normalize_text(p) in normalized for p in LOCATION_PHRASES)
    
    def get_greeting(self, text):
        normalized = self.normalize_text(text)
        for phrases, responses in GREETINGS:
            for phrase in phrases:
                if normalized.startswith(self.normalize_text(phrase)):
                    return random.choice(responses)
        return None
    
    def violation_reason(self, text):
        normalized = self.normalize_text(text).strip()
        
        if normalized in ["خاص", "الخاص"]:
            return "خاص"
        
        for word in BAD_WORDS:
            if self.normalize_text(word) in normalized:
                return "إساءة"
        
        for phrase in INAPPROPRIATE:
            if self.normalize_text(phrase) in normalized:
                return "كلام غير مناسب"
        
        return None
    
    def is_forwarded(self, message):
        return bool(
            getattr(message, "forward_origin", None) or
            getattr(message, "forward_from", None) or
            getattr(message, "forward_from_chat", None) or
            getattr(message, "forward_sender_name", None)
        )
    
    def forbidden_link(self, text):
        if not text:
            return False
        
        url_pattern = re.compile(r"(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)", re.IGNORECASE)
        
        for link in url_pattern.findall(text):
            link = link.rstrip(".,!?؟،؛:)]}>\"'")
            normalized = link.lower().rstrip("/")
            
            if normalized.startswith(GROUP_LINK.lower().rstrip("/")):
                continue
            
            if any(domain in normalized for domain in ["maps.google.com", "goo.gl/maps", "maps.app.goo.gl"]):
                continue
            
            return True
        
        return False
    
    async def is_admin(self, update, context):
        user = update.effective_user
        if not user:
            return False
        
        if user.id in ADMIN_IDS:
            return True
        
        if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
            return True
        
        try:
            member = await context.bot.get_chat_member(GROUP_ID, user.id)
            return member.status in ["administrator", "creator"]
        except:
            return False
    
    def get_role_badge(self, user_id):
        if self.db.is_driver(user_id):
            return DRIVER_BADGE
        if self.db.is_customer(user_id):
            return CUSTOMER_BADGE
        return ""
    
    def display_user(self, user):
        if not user:
            return "عضو"
        name = self.html(user.full_name)
        badge = self.get_role_badge(user.id)
        if badge:
            return f"<b>{self.html(badge)} {name}</b>"
        return f"<b>{name}</b>"
    
    async def welcome_new_member(self, update, context):
        message = update.message
        
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            
            self.db.save_user(member)
            
            welcome_text = f"""
🌟 <b>يا هلا {self.html(member.full_name)}!</b>

نورت <b>{GROUP_NAME}</b> 🚘

━━━━━━━━━━━━━━━━

👤 <b>إذا أنت عميل:</b>
اكتب طلبك مباشرة مثل:
«مشوار من الفضيلة إلى الرغامة»

🚕 <b>إذا أنت كابتن:</b>
إذا شفت طلب يناسبك:
↩️ <b>اقتبس رسالة العميل</b> واكتب «جاهز»

━━━━━━━━━━━━━━━━

✍️ <b>للتسجيل:</b>
اكتب «أنا كابتن» أو «أنا عميل»
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👤 أنا عميل", callback_data=f"role_customer:{member.id}"),
                    InlineKeyboardButton("🚕 أنا كابتن", callback_data=f"role_driver:{member.id}"),
                ],
                [
                    InlineKeyboardButton("📋 قانون القروب", callback_data="rules"),
                    InlineKeyboardButton("📩 الإدارة", url=f"https://t.me/{ADMIN_USERNAME}"),
                ],
            ])
            
            await message.reply_text(welcome_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    
    async def member_left(self, update, context):
        message = update.message
        left_member = message.left_chat_member
        
        if left_member.is_bot:
            return
        
        self.db.save_user(left_member)
        
        badge = self.get_role_badge(left_member.id)
        badge_text = f"\n🏷️ <b>الصفة:</b> {self.html(badge)}" if badge else ""
        
        username_text = f"\n🔹 <b>اليوزر:</b> @{self.html(left_member.username)}" if left_member.username else ""
        
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""
🚨 <b>تنبيه مغادرة عضو</b>

👤 <b>الاسم:</b> {self.html(left_member.full_name)}
{username_text}
{badge_text}

🆔 <b>ID:</b> <code>{left_member.id}</code>
👋 غادر القروب
📍 <b>القروب:</b> {self.html(GROUP_NAME)}
                """,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error sending left notification: {e}")
    
    async def role_selection(self, update, context):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        if data.startswith("role_customer:"):
            role = "customer"
        elif data.startswith("role_driver:"):
            role = "driver"
        else:
            return
        
        target_id = int(data.split(":")[1])
        
        if user.id != target_id and not await self.is_admin(update, context):
            await query.answer("هذا الزر مخصص للعضو الجديد فقط!", show_alert=True)
            return
        
        self.db.save_user(user)
        self.db.set_role(target_id, role)
        
        if role == "customer":
            confirm_text = f"""
✅ <b>تم تسجيلك كعميل!</b>

👤 <b>طريقة طلب المشوار:</b>
اكتب طلبك مباشرة في القروب

📝 <b>مثال:</b>
«مشوار من الفضيلة إلى الرغامة»
            """
        else:
            confirm_text = f"""
✅ <b>تم تسجيلك ككابتن!</b>

🚕 <b>طريقة قبول المشوار:</b>
اقتبس رسالة العميل واكتب «جاهز»

📍 <b>أعلن موقعك مرة يومياً:</b>
اكتب «موجود في الحمدانية لأي مشوار»
            """
        
        await query.message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
    
    async def show_rules(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)
    
    async def handle_message(self, update, context):
        message = update.message
        user = update.effective_user
        
        if not message or not user:
            return
        
        self.db.save_user(user)
        
        text = message.text or ""
        
        if not text:
            return
        
        self.db.add_points(user.id, POINTS_SYSTEM["message"])
        
        normalized_text = self.normalize_text(text).strip()
        
        if normalized_text in ["انا كابتن", "انا سايق", "انا سواق"]:
            self.db.save_user(user)
            self.db.set_role(user.id, "driver")
            await message.reply_text(
                f"✅ <b>تم تسجيلك ككابتن!</b>\n\n"
                f"🚕 <b>طريقة قبول المشوار:</b>\n"
                f"اقتبس رسالة العميل واكتب «جاهز»\n\n"
                f"📍 <b>أعلن موقعك مرة يومياً:</b>\n"
                f"اكتب «موجود في الحمدانية لأي مشوار»",
                parse_mode=ParseMode.HTML
            )
            return
        
        if normalized_text in ["انا عميل", "انا زبون", "انا طالب"]:
            self.db.save_user(user)
            self.db.set_role(user.id, "customer")
            await message.reply_text(
                f"✅ <b>تم تسجيلك كعميل!</b>\n\n"
                f"👤 <b>طريقة طلب المشوار:</b>\n"
                f"اكتب طلبك مباشرة مثل:\n"
                f"«مشوار من الفضيلة إلى الرغامة»",
                parse_mode=ParseMode.HTML
            )
            return
        
        if self.is_forwarded(message) and not await self.is_admin(update, context):
            try:
                await message.delete()
            except:
                pass
            await message.reply_text(f"⚠️ {self.display_user(user)}\n\nالرسائل المحولة ممنوعة 🚫", parse_mode=ParseMode.HTML)
            return
        
        if self.forbidden_link(text) and not await self.is_admin(update, context):
            try:
                await message.delete()
            except:
                pass
            await message.reply_text(f"⚠️ {self.display_user(user)}\n\nالروابط ممنوعة 🚫\n📍 روابط Google Maps مسموحة فقط", parse_mode=ParseMode.HTML)
            return
        
        reason = self.violation_reason(text)
        if reason and not await self.is_admin(update, context):
            await self.handle_violation(update, context, reason)
            return
        
        if self.is_ready_reply(text):
            self.db.add_points(user.id, POINTS_SYSTEM["driver_ready"])
            await self.handle_ready_reply(update, context)
            return
        
        if self.looks_like_trip(text):
            self.db.add_points(user.id, POINTS_SYSTEM["trip_request"])
            await self.handle_trip_request(update, context, text)
            return
        
        if self.looks_like_location(text):
            if not self.db.is_driver(user.id):
                self.db.save_user(user)
                self.db.set_role(user.id, "driver")
            self.db.add_points(user.id, POINTS_SYSTEM["location"])
            await self.handle_location(update, context, text)
            return
        
        chat_response = self.get_chat_response(text)
        if chat_response:
            await message.reply_text(chat_response)
            return
        
        greeting = self.get_greeting(text)
        if greeting and not self.looks_like_trip(text):
            await message.reply_text(greeting)
            return
    
    async def handle_trip_request(self, update, context, text):
        message = update.message
        user = update.effective_user
        
        pickup, destination = self.extract_route(text)
        
        if not pickup or not destination:
            return
        
        trip_type = self.detect_trip_type(text)
        price = self.extract_price(text)
        
        self.db.create_trip(
            message_id=message.message_id,
            customer_id=user.id,
            pickup=pickup,
            destination=destination,
            trip_type=trip_type,
            price=price
        )
        
        type_badge = "🔄 شهري" if trip_type == "monthly" else "🚗 عادي"
        
        if price:
            price_text = f"\n💰 <b>السعر المقترح:</b> {price} ريال"
        else:
            price_text = "\n💰 <b>السعر:</b> بالتفاهم"
        
        confirm_text = f"""
✅ <b>تم تسجيل طلبك!</b>

📋 <b>نوع المشوار:</b> {type_badge}
📍 <b>من:</b> {self.html(pickup)}
🎯 <b>إلى:</b> {self.html(destination)}
{price_text}

🚕 <b>للكباتن:</b>
اقتبسوا هذه الرسالة واكتبوا «جاهز»
        """
        
        confirm_message = await message.reply_text(confirm_text, parse_mode=ParseMode.HTML)
        
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("""
                UPDATE trips SET confirm_message_id = ?
                WHERE message_id = ?
            """, (confirm_message.message_id, message.message_id))
            con.commit()
    
    async def handle_ready_reply(self, update, context):
        message = update.message
        driver = update.effective_user
        
        if not message.reply_to_message:
            await message.reply_text(
                "⚠️ <b>تنبيه!</b>\n\nلأخذ مشوار، لازم <b>تقتبس رسالة العميل</b> وترد عليها بكلمة «جاهز»",
                parse_mode=ParseMode.HTML
            )
            return
        
        replied_message = message.reply_to_message
        
        # البحث عن الرحلة بكل الطرق
        trip = self.db.get_trip_by_message(replied_message.message_id)
        
        if not trip:
            trip = self.db.get_trip_by_confirm_message(replied_message.message_id)
        
        if not trip:
            with self.db.connect() as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM trips ORDER BY trip_id DESC LIMIT 1")
                row = cur.fetchone()
                if row:
                    trip = dict(row)
        
        if not trip:
            await message.reply_text(
                "⚠️ هذه ليست رسالة طلب مشوار!\n"
                "رد على رسالة العميل الأصلية\n"
                "أو على رسالة تأكيد البوت ✅",
                parse_mode=ParseMode.HTML
            )
            return
        
        if trip["customer_id"] == driver.id:
            await message.reply_text("😂 ما تقدر تأخذ مشوارك بنفسك!", parse_mode=ParseMode.HTML)
            return
        
        self.db.save_user(driver)
        
        if not self.db.is_driver(driver.id):
            self.db.set_role(driver.id, "driver")
        
        added = self.db.add_ready_driver(trip["trip_id"], driver.id)
        
        if not added:
            await message.reply_text("✅ أنت مسجل جاهز لهذا المشوار بالفعل!", parse_mode=ParseMode.HTML)
            return
        
        type_badge = "🔄 شهري" if trip["trip_type"] == "monthly" else "🚗 عادي"
        
        driver_price = self.extract_price(message.text or "")
        
        if driver_price and trip.get("price"):
            if driver_price != trip["price"]:
                price_text = f"\n💰 <b>سعر الكابتن:</b> {driver_price} ريال"
            else:
                price_text = f"\n💰 <b>السعر:</b> {driver_price} ريال"
        elif trip.get("price"):
            price_text = f"\n💰 <b>السعر:</b> {trip['price']} ريال"
        else:
            price_text = "\n💰 <b>السعر:</b> بالتفاهم"
        
        card_text = f"""
🚕 <b>كابتن جاهز!</b>

👨‍✈️ <b>الكابتن:</b> {self.html(driver.full_name)}

📋 <b>نوع المشوار:</b> {type_badge}
📍 <b>من:</b> {self.html(trip["pickup"])}
🎯 <b>إلى:</b> {self.html(trip["destination"])}
{price_text}

━━━━━━━━━━━━━━━━
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📩 التواصل مع العميل", callback_data=f"contact_customer:{trip['trip_id']}:{driver.id}"),
            ],
            [
                InlineKeyboardButton("🚕 التواصل مع الكابتن", callback_data=f"contact_driver:{trip['trip_id']}:{driver.id}"),
            ],
        ])
        
        await message.reply_text(card_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        
        await message.reply_text(random.choice(READY_MESSAGES), parse_mode=ParseMode.HTML)
    
    async def handle_location(self, update, context, text):
        message = update.message
        driver = update.effective_user
        
        if not self.db.is_driver(driver.id):
            await message.reply_text(
                "📍 هذا الإعلان مخصص للكباتن فقط 🚕\n\n"
                "إذا أنت كابتن اضغط «🚕 أنا كابتن» مرة واحدة",
                parse_mode=ParseMode.HTML
            )
            return
        
        already_posted = self.db.check_location_today(driver.id)
        
        if already_posted:
            await message.reply_text(
                "😂 عرفنا وينك اليوم.\n\n📍 إعلان التواجد مسموح مرة واحدة فقط باليوم",
                parse_mode=ParseMode.HTML
            )
            return
        
        await message.reply_text(
            f"📍 <b>تم تسجيل تواجد الكابتن</b>\n\n"
            f"{self.display_user(driver)}\n\n"
            f"📌 {self.html(text)}\n\n"
            f"🚕 تم تسجيل موقعك، الله يرزقك مشوار طيب",
            parse_mode=ParseMode.HTML
        )
    
    async def handle_violation(self, update, context, reason):
        message = update.message
        user = update.effective_user
        
        try:
            await message.delete()
        except:
            pass
        
        count = self.db.add_violation(user.id)
        
        if reason == "خاص":
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=f"⚠️ {self.display_user(user)}\n\n🚫 ممنوع كتابة «خاص»\n📝 تم تسجيلها كمخالفة",
                parse_mode=ParseMode.HTML
            )
        
        if count >= 4:
            try:
                until = datetime.now(SAUDI_TZ) + timedelta(hours=MUTE_HOURS)
                await context.bot.restrict_chat_member(
                    GROUP_ID, user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until
                )
                await context.bot.send_message(
                    GROUP_ID,
                    f"🔇 <b>تم كتم العضو</b>\n\n{self.display_user(user)}\n\n🔴 المخالفة رقم <b>{count}</b>\n⏱ مدة الكتم: <b>24 ساعة</b>",
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Mute error: {e}")
        
        elif count == 3:
            await context.bot.send_message(
                GROUP_ID,
                f"🔴 <b>المخالفة الثالثة</b>\n\n{self.display_user(user)}\n\n⚠️ هذه آخر مخالفة قبل الكتم",
                parse_mode=ParseMode.HTML
            )
        
        elif count == 2:
            await context.bot.send_message(
                GROUP_ID,
                f"🟠 <b>المخالفة الثانية</b>\n\n{self.display_user(user)}\n\nالسبب: {self.html(reason)}",
                parse_mode=ParseMode.HTML
            )
        
        else:
            await context.bot.send_message(
                GROUP_ID,
                f"🟡 <b>تنبيه للمرة الأولى</b>\n\n{self.display_user(user)}\n\nالسبب: {self.html(reason)}",
                parse_mode=ParseMode.HTML
            )
    
    async def contact_customer(self, update, context):
        query = update.callback_query
        user = query.from_user
        
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        if user.id != driver_id:
            await query.answer("هذا الزر مخصص للكابتن المسجل!", show_alert=True)
            return
        
        if not self.db.is_driver_ready(trip_id, driver_id):
            await query.answer("أنت غير مسجل لهذا المشوار!", show_alert=True)
            return
        
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cur.fetchone()
            trip = dict(row) if row else None
        
        if trip:
            await query.answer("📩 فتح تواصل العميل...", url=f"tg://user?id={trip['customer_id']}")
    
    async def contact_driver(self, update, context):
        query = update.callback_query
        user = query.from_user
        
        data = query.data.split(":")
        trip_id = int(data[1])
        driver_id = int(data[2])
        
        with self.db.connect() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,))
            row = cur.fetchone()
            trip = dict(row) if row else None
        
        if not trip or trip["customer_id"] != user.id:
            await query.answer("هذا الزر مخصص لصاحب الطلب فقط!", show_alert=True)
            return
        
        await query.answer("🚕 فتح تواصل الكابتن...", url=f"tg://user?id={driver_id}")
    
    async def cmd_start(self, update, context):
        await update.message.reply_text(
            f"🚘 <b>أهلاً بك في {GROUP_NAME}</b>\n\n"
            "🤖 البوت يعمل بنجاح ✅\n\n"
            "📋 /rules - القوانين\n"
            "ℹ️ /help - المساعدة\n"
            "🏆 /top - لوحة الصدارة",
            parse_mode=ParseMode.HTML
        )
    
    async def cmd_rules(self, update, context):
        await update.message.reply_text(RULES_TEXT, parse_mode=ParseMode.HTML)
    
    async def cmd_help(self, update, context):
        help_text = f"""
🤖 <b>طريقة استخدام البوت</b>

👤 <b>للعميل:</b>
اكتب مشوارك مباشرة:
«مشوار من الفضيلة إلى الرغامة»

🚕 <b>للكابتن:</b>
اقتبس رسالة العميل أو رسالة التأكيد واكتب «جاهز»

✍️ <b>التسجيل:</b>
اكتب «أنا كابتن» أو «أنا عميل»

💬 <b>سوالف:</b>
اكتب أي شي وأنا أرد عليك!

📩 <b>الإدارة:</b> @{ADMIN_USERNAME}
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def cmd_top(self, update, context):
        rows = self.db.get_top_users(10)
        
        if not rows:
            await update.message.reply_text("📊 لا يوجد نقاط بعد!")
            return
        
        text = "🏆 <b>لوحة الصدارة</b>\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, row in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i+1}️⃣"
            text += f"{medal} {self.html(row['name'])} - {row['points']} نقطة\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
    async def smart_reminder(self, context):
        current_hour = datetime.now(SAUDI_TZ).hour
        
        if 2 <= current_hour < 8:
            return
        
        text = random.choice(REMINDERS).format(
            GROUP_NAME=GROUP_NAME,
            GROUP_LINK=GROUP_LINK
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📤 نشر رابط القروب", url=f"https://t.me/share/url?url={GROUP_LINK}&text=🚘 انضموا لقروب مشاوير جدة"),
            ],
            [
                InlineKeyboardButton("🚘 فتح القروب", url=GROUP_LINK),
            ],
        ])
        
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Reminder error: {e}")
    
    async def engagement_reminder(self, context):
        current_hour = datetime.now(SAUDI_TZ).hour
        
        if 2 <= current_hour < 7:
            return
        
        text = random.choice(ENGAGEMENT_MESSAGES)
        
        try:
            await context.bot.send_message(
                chat_id=GROUP_ID,
                text=text,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Engagement error: {e}")
    
    def run(self):
        app = Application.builder().token(TOKEN).build()
        
        app.job_queue.run_repeating(
            self.engagement_reminder,
            interval=ENGAGEMENT_INTERVAL,
            first=60
        )
        
        app.job_queue.run_repeating(
            self.smart_reminder,
            interval=REMINDER_INTERVAL,
            first=REMINDER_INTERVAL
        )
        
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("rules", self.cmd_rules))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("top", self.cmd_top))
        
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.welcome_new_member))
        app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.member_left))
        
        app.add_handler(CallbackQueryHandler(self.role_selection, pattern="^role_"))
        app.add_handler(CallbackQueryHandler(self.show_rules, pattern="^rules$"))
        app.add_handler(CallbackQueryHandler(self.contact_customer, pattern="^contact_customer:"))
        app.add_handler(CallbackQueryHandler(self.contact_driver, pattern="^contact_driver:"))
        
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("✅ البوت يعمل...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

# ============================================================
# 🚀 نقطة البداية
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # حذف قاعدة البيانات القديمة
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("✅ تم حذف قاعدة البيانات القديمة")
    
    bot = SmartRidesBot()
    bot.run()
