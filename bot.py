import logging
import os
import asyncio
import signal

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

# =========================
# LOCK (NON-FATAL SAFE MODE)
# =========================
LOCK_FILE = "/tmp/ceyona_bot.lock"


def ensure_single_instance():
    """
    Cloud-safe lock:
    - NEVER crashes bot
    - only prevents silent duplicates (best-effort)
    """

    try:
        pid = str(os.getpid())

        # overwrite lock always (Railway-safe approach)
        with open(LOCK_FILE, "w") as f:
            f.write(pid)

        logger.info(f"[LOCK] acquired by pid={pid}")

    except Exception as e:
        logger.warning(f"[LOCK WARNING] {e}")


def cleanup_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.info("[LOCK] cleaned")
    except Exception as e:
        logger.warning(f"[LOCK CLEANUP FAILED] {e}")


# =========================
# MESSAGE HANDLER
# =========================
async def message_handler(update: Update, context):
    try:
        if not update or not update.message:
            return

        text = update.message.text or ""
        text = text.strip()

        if not text:
            return

        user_id = update.effective_user.id if update.effective_user else 0

        logger.info(f"[IN] user={user_id}")

        response = await asyncio.wait_for(
            handle_message(user_id, text),
            timeout=45
        )

        response = response or "No response generated."

        await update.message.reply_text(response)

        logger.info(f"[OUT] user={user_id} OK")

    except asyncio.TimeoutError:
        logger.warning("[TIMEOUT] handler")
        try:
            await update.message.reply_text("Request timeout. Try again.")
        except:
            pass

    except Exception as e:
        logger.exception(f"[BOT ERROR] {e}")
        try:
            await update.message.reply_text("System error. Try again.")
        except:
            pass


# =========================
# SIGNAL HANDLING (CLEAN SHUTDOWN)
# =========================
def setup_signals():
    def shutdown(signum, frame):
        logger.info(f"[SHUTDOWN] signal={signum}")
        cleanup_lock()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


# =========================
# BOT START
# =========================
def start_bot(settings):
    ensure_single_instance()
    setup_signals()

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # =========================
    # SAFE POST INIT
    # =========================
    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("[INIT] webhook cleared")

        except Exception as e:
            logger.warning(f"[POST_INIT ERROR] {e}")

    app.post_init = post_init

    # =========================
    # HANDLER
    # =========================
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    logger.info("BOT STARTED (CLOUD STABLE MODE)")

    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )
    finally:
        cleanup_lock()