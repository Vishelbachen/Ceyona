import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

_bot_instance = None


def start_bot(settings):
    global _bot_instance

    if _bot_instance:
        logger.error("Bot instance already exists!")
        return

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

    async def post_init(app):
        # 🔥 HARD RESET TELEGRAM UPDATES STREAM
        await app.bot.delete_webhook(drop_pending_updates=True)
        try:
            await app.bot.get_updates(offset=-1)
        except Exception:
            pass

        logger.info("Webhook cleaned + updates reset")

    app.post_init = post_init

    _bot_instance = app

    logger.info("BOT START (SINGLE INSTANCE SAFE MODE)")

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )