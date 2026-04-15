import logging
import asyncio
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
# SAFE MESSAGE EXTRACTOR
# =========================
def extract_message(update: Update):
    if not update:
        return None

    return (
        update.message
        or update.edited_message
        or update.channel_post
        or update.edited_channel_post
    )


# =========================
# SAFE HANDLER WRAPPER
# =========================
async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = extract_message(update)

        if not message:
            return

        text = getattr(message, "text", None) or getattr(message, "caption", None)

        if not text:
            return

        text = text.strip()
        if not text:
            return

        user_id = update.effective_user.id if update.effective_user else 0

        logger.info(f"[BOT] IN | user={user_id}")

        # 🔥 TIMEOUT PROTECTION (VERY IMPORTANT)
        try:
            response = await asyncio.wait_for(
                handle_message(user_id, text),
                timeout=45
            )
        except asyncio.TimeoutError:
            response = "Request timeout. Please try again."

        if not response:
            response = "No response generated."

        await message.reply_text(response)

        logger.info(f"[BOT] OUT | success")

    except Exception as e:
        logger.exception(f"[BOT] handler crash: {e}")

        try:
            await message.reply_text("System error. Try again.")
        except Exception:
            pass


# =========================
# START BOT (RAILWAY SAFE)
# =========================
def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # 🔥 catch everything (no silent updates lost)
    app.add_handler(MessageHandler(filters.ALL, message_entry))

    logger.info("[BOT] Initializing bot...")

    # 🔥 IMPORTANT: clean webhook (Railway fix)
    async def post_init(application):
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("[BOT] Webhook cleared")

    app.post_init = post_init

    # 🚀 START
    logger.info("[BOT] Starting polling...")
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
    )