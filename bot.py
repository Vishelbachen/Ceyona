import logging
import asyncio
import os  # 🔥 FIX CRITICAL

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
# START BOT (HYBRID MODE)
# =========================
def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    # =========================
    # POST INIT (WEBHOOK SAFE)
    # =========================
    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)

            # =========================
            # WEBHOOK MODE
            # =========================
            if settings.WEBHOOK_URL:
                await application.bot.set_webhook(
                    url=settings.WEBHOOK_URL + "/webhook",
                    drop_pending_updates=True
                )
                logger.info("[WEBHOOK] enabled mode")

            else:
                logger.warning("[WEBHOOK] missing → fallback to polling mode")

        except Exception as e:
            logger.error(f"[POST_INIT ERROR] {e}")

    app.post_init = post_init

    # =========================
    # MODE SWITCH (AUTO)
    # =========================
    if settings.WEBHOOK_URL:

        logger.info("BOT STARTED (WEBHOOK MODE)")

        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            webhook_path="/webhook",
            drop_pending_updates=True
        )

    else:

        logger.info("BOT STARTED (POLLING FALLBACK MODE)")

        app.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )