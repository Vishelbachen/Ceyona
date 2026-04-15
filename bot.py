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


# =========================
# MESSAGE RESOLVER (ROBUST)
# =========================
def extract_message(update: Update):
    """
    Safely extracts ANY message type:
    - text
    - edited text
    - captions (future extension)
    """
    if not update:
        return None

    message = (
        update.message
        or update.edited_message
        or update.channel_post
        or update.edited_channel_post
    )

    return message


# =========================
# HANDLER
# =========================
async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = extract_message(update)

        if not message:
            logger.warning("[BOT] No message in update")
            return

        text = getattr(message, "text", None)

        if not text:
            text = getattr(message, "caption", None)

        if not text:
            logger.warning("[BOT] Empty non-text message ignored")
            return

        text = text.strip()
        user_id = update.effective_user.id if update.effective_user else None

        logger.info(f"[BOT] IN | user_id={user_id} | text={text}")

        response = await handle_message(user_id, text)

        if not response:
            response = "No response generated."

        await message.reply_text(response)

        logger.info("[BOT] OUT | response sent")

    except Exception as e:
        logger.exception(f"[BOT] message_entry failed: {e}")


# =========================
# START BOT (CLEAN LIFECYCLE)
# =========================
def start_bot(settings):
    """
    IMPORTANT:
    run_polling MUST NOT be awaited (PTB design)
    """
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # Catch ALL updates (no silent loss)
    app.add_handler(
        MessageHandler(filters.ALL, message_entry)
    )

    logger.info("[BOT] Starting application...")

    # Single lifecycle entry (NO initialize/start manual calls)
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
    )