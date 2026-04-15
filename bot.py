import os
import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

LOCK_FILE = "/tmp/bot.lock"


def start_bot(settings):

    # 🧠 BLOCK DOUBLE START
    if os.path.exists(LOCK_FILE):
        raise RuntimeError("Bot already running (lock detected)")

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    async def handle(update, context):
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        user_id = update.effective_user.id

        response = await handle_message(user_id, text)
        await update.message.reply_text(response or "No response")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    logger.info("BOT START SINGLE INSTANCE MODE")

    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )