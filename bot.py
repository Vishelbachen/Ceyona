import logging
import asyncio
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from handler import handle_message

logger = logging.getLogger(__name__)


# =========================
# MESSAGE HANDLER
# =========================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message:
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
# BOT START (CLEAN WEBHOOK MODE)
# =========================
def start_bot(settings):

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    # =========================
    # INIT WEBHOOK
    # =========================
    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)

            if settings.WEBHOOK_URL:
                await application.bot.set_webhook(
                    url=settings.WEBHOOK_URL + "/webhook",
                    drop_pending_updates=True
                )

            logger.info("[INIT] webhook ready")

        except Exception as e:
            logger.error(f"[INIT ERROR] {e}")

    app.post_init = post_init

    logger.info("BOT STARTED (PRO WEBHOOK MODE)")

    # =========================
    # RAILWAY ENTRY POINT
    # =========================
    app.run_polling(
        drop_pending_updates=True,
        close_loop=False
    )