import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)


def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    async def handler(update: Update, context):
        try:
            if not update.message or not update.message.text:
                return

            text = update.message.text.strip()
            user_id = update.effective_user.id

            response = await handle_message(user_id, text)

            await update.message.reply_text(response or "No response")

        except Exception as e:
            logger.exception(e)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

    logger.info("BOT STARTING (CLEAN MODE)")

    # 🔥 CRITICAL FIX: ONLY ONE CONTROL MODE
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )