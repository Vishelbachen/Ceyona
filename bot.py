import logging
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

# =========================
# SINGLE INSTANCE GUARD
# =========================
LOCK_FILE = "/tmp/ceyona_bot.lock"


def ensure_single_instance():
    if os.path.exists(LOCK_FILE):
        raise RuntimeError("Bot already running (lock exists)")

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def cleanup_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.warning(f"[LOCK CLEANUP FAILED] {e}")


# =========================
# HANDLER WRAPPER
# =========================
async def message_handler(update: Update, context):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        if not text:
            return

        user_id = update.effective_user.id

        logger.info(f"[IN] user={user_id} text={text}")

        response = await asyncio.wait_for(
            handle_message(user_id, text),
            timeout=45
        )

        if not response:
            response = "No response generated."

        await update.message.reply_text(response)

        logger.info(f"[OUT] success user={user_id}")

    except asyncio.TimeoutError:
        logger.warning("[TIMEOUT] handler exceeded limit")
        await update.message.reply_text("Request timeout. Try again.")

    except Exception as e:
        logger.exception(f"[BOT ERROR] {e}")
        await update.message.reply_text("System error. Try again.")


# =========================
# BOT START
# =========================
def start_bot(settings):
    ensure_single_instance()

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # =========================
    # TELEGRAM CLEAN INIT
    # =========================
    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("[INIT] Webhook cleared")

            # HARD reset updates stream
            try:
                await application.bot.get_updates(offset=-1)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"[POST_INIT ERROR] {e}")

    app.post_init = post_init

    # =========================
    # HANDLER
    # =========================
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    logger.info("BOT STARTED (PRODUCTION SAFE MODE)")

    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )
    finally:
        cleanup_lock()