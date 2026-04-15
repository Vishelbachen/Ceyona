

import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)


def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    async def handle(update: Update, context):
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        user_id = update.effective_user.id

        try:
            response = await handle_message(user_id, text)
            await update.message.reply_text(response or "No response")
        except Exception as e:
            logger.exception(e)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    logger.info("BOT START (CLEAN MODE)")

    # 🔥 ONLY THIS
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )

async def post_init(application):
    # kill EVERYTHING Telegram knows
    await application.bot.delete_webhook(drop_pending_updates=True)

    # HARD reset updates stream
    try:
        await application.bot.get_updates(offset=-1)
    except Exception:
        pass