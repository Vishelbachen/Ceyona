import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

from handler import handle_message

logger = logging.getLogger(__name__)


async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update:
            return

        message = update.message or update.edited_message

        if not message or not message.text:
            logger.warning("[BOT] Non-text or empty message")
            return

        user_id = update.effective_user.id
        text = message.text.strip()

        logger.info(f"[BOT] Incoming | user_id={user_id} | text={text}")

        response = await handle_message(user_id, text)

        await message.reply_text(response or "No response generated.")

        logger.info("[BOT] Response sent")

    except Exception as e:
        logger.exception(f"[BOT] Error: {e}")


async def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # IMPORTANT: broader filter (fix silent messages)
    app.add_handler(
        MessageHandler(filters.ALL, message_entry)
    )

    logger.info("[BOT] Starting application")

    await app.run_polling(
        drop_pending_updates=True
    )