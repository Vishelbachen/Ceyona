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
# GLOBAL LOCK (ANTI DOUBLE INSTANCE)
# =========================
BOT_LOCK = asyncio.Lock()


def extract_message(update: Update):
    if not update:
        return None

    return (
        update.message
        or update.edited_message
        or update.channel_post
        or update.edited_channel_post
    )


async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with BOT_LOCK:  # 🔥 protects parallel overload
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

            try:
                response = await asyncio.wait_for(
                    handle_message(user_id, text),
                    timeout=60
                )
            except asyncio.TimeoutError:
                response = "Request timeout. Try again."

            response = response or "No response generated."

            await message.reply_text(response)

            logger.info(f"[BOT] OUT | OK")

        except Exception as e:
            logger.exception(f"[BOT] crash: {e}")

            try:
                await message.reply_text("System error. Try again.")
            except Exception:
                pass


def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # 🔥 catch all updates
    app.add_handler(MessageHandler(filters.ALL, message_entry))

    logger.info("[BOT] Initializing...")

    async def post_init(application):
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("[BOT] Webhook cleared")

    app.post_init = post_init

    logger.info("[BOT] Starting polling (SINGLE INSTANCE MODE)...")

    # 🔥 ONLY ONE ENTRY POINT
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False,
    )