import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)


# =========================
# SETTINGS
# =========================

TOKEN = os.getenv("BOT_TOKEN")

GROUP_ID = -1003716441020

GROUP_NAME = "🚘 مشاوير جدة • مكة • الطائف • جميع المناطق"

ADMIN_USERNAME = "klodi500"


# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# CHECK TOKEN
# =========================

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN غير موجود في GitHub Secrets"
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    await update.message.reply_text(
        f"🚘 أهلاً بك في {GROUP_NAME}\n\n"
        "🤖 البوت يعمل بنجاح ✅\n\n"
        "📋 /rules — القوانين\n"
        "ℹ️ /help — المساعدة"
    )


# =========================
# RULES
# =========================

async def rules(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    await update.message.reply_text(
        f"""
📋 قوانين {GROUP_NAME}

1️⃣ القروب للمشاوير والنقل.

2️⃣ العميل يكتب طلب المشوار بوضوح.

3️⃣ الكابتن الجاهز يتواصل مع العميل.

4️⃣ 💰 السعر والتفاهم بالخاص.

5️⃣ 🚫 يمنع السب والإساءة.

6️⃣ 🚫 يمنع نشر الروابط والإعلانات.

7️⃣ 🤝 الاحترام واجب على الجميع.

📩 الإدارة:
@{ADMIN_USERNAME}
"""
    )


# =========================
# HELP
# =========================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    await update.message.reply_text(
        "🤖 أوامر البوت:\n\n"
        "/start — تشغيل البوت\n"
        "/rules — عرض القوانين\n"
        "/help — المساعدة"
    )


# =========================
# ERROR
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "حدث خطأ:",
        exc_info=context.error
    )


# =========================
# MAIN
# =========================

def main():

    print(
        "====================================",
        flush=True
    )

    print(
        "🚗 Starting Jeddah Rides Bot...",
        flush=True
    )

    print(
        "====================================",
        flush=True
    )

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "rules",
            rules
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_error_handler(
        error_handler
    )

    print(
        "✅ Bot is running...",
        flush=True
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
