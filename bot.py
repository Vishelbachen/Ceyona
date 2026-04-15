import logging
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes
)

from handler import handle_message

logger = logging.getLogger(__name__)


# =========================
# SAFE HANDLER
# =========================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update or not update.message:
            return

        text = (update.message.text or "").strip()
        if not text:
            return

        user_id = update.effective_user.id

        logger.info(f"[IN] user={user_id}")

        response = await asyncio.wait_for(
            handle_message(user_id, text),
            timeout=45
        )

        await update.message.reply_text(response or "No response")

        logger.info(f"[OUT] user={user_id}")

    except asyncio.TimeoutError:
        await update.message.reply_text("Request timeout. Try again.")

    except Exception as e:
        logger.exception(f"[BOT ERROR] {e}")
        try:
            await update.message.reply_text("System error. Try again.")
        except:
            pass


# =========================
# START BOT (WEBHOOK MODE)
# =========================
def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    async def post_init(application):
        try:
            # 🔥 CRITICAL: remove polling entirely
            await application.bot.delete_webhook(drop_pending_updates=True)

            # set webhook to Railway URL
            # IMPORTANT: replace with your real URL
            webhook_url = settings.WEBHOOK_URL

            await application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )

            logger.info("[WEBHOOK] set successfully")

        except Exception as e:
            logger.error(f"[WEBHOOK ERROR] {e}")

    app.post_init = post_init

    logger.info("BOT STARTED (WEBHOOK MODE)")

    # 🚀 webhook server instead of polling
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_path="/webhook",
        drop_pending_updates=True
    )