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
# MESSAGE HANDLER
# =========================
async def message_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update or not update.message:
            logger.warning("[BOT] Empty update received")
            return

        if not update.message.text:
            logger.warning("[BOT] Non-text message ignored")
            return

        user_id = update.effective_user.id
        text = update.message.text.strip()

        logger.info(f"[BOT] Incoming message | user_id={user_id} | text={text}")

        response = await handle_message(user_id, text)

        if not response:
            response = "No response generated."

        await update.message.reply_text(response)

        logger.info("[BOT] Response sent successfully")

    except Exception as e:
        logger.exception(f"[BOT] message_entry failed: {e}")

        try:
            await update.message.reply_text(
                "System error occurred. Please try again."
            )
        except Exception:
            pass


# =========================
# BOT START
# =========================
async def start_bot(settings):
    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # handler registration
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_entry)
    )

    # lifecycle start
    await app.initialize()
    await app.start()

    logger.info("[BOT] Bot initialized")

    # IMPORTANT: clean webhook (polling mode safety)
    await app.bot.delete_webhook(drop_pending_updates=True)

    logger.info("[BOT] Webhook cleared, starting polling")

    # =========================
    # PRODUCTION SAFE LOOP
    # =========================
    await app.run_polling(
        close_loop=False,
        drop_pending_updates=True
    )