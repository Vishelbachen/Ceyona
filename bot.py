import logging
import os
import asyncio
import signal

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

# =========================
# LOCK CONFIG
# =========================
LOCK_FILE = "/tmp/ceyona_bot.lock"


# =========================
# SAFE SINGLE INSTANCE GUARD
# =========================
def ensure_single_instance():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())

            # check if process exists
            os.kill(old_pid, 0)

            # process alive → block start
            raise RuntimeError("Bot already running (active process detected)")

        except ProcessLookupError:
            # dead process → remove stale lock
            logger.warning("[LOCK] stale process removed")
            os.remove(LOCK_FILE)

        except Exception:
            # broken lock → remove
            logger.warning("[LOCK] corrupted lock removed")
            os.remove(LOCK_FILE)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def cleanup_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.warning(f"[LOCK CLEANUP FAILED] {e}")


# =========================
# MESSAGE HANDLER
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

        response = response or "No response generated."

        await update.message.reply_text(response)

        logger.info(f"[OUT] user={user_id} OK")

    except asyncio.TimeoutError:
        logger.warning("[TIMEOUT] message handler")
        await update.message.reply_text("Request timeout. Try again.")

    except Exception as e:
        logger.exception(f"[BOT ERROR] {e}")
        await update.message.reply_text("System error. Try again.")


# =========================
# GRACEFUL SHUTDOWN
# =========================
def setup_signal_handlers():
    def shutdown(signum, frame):
        logger.info("Shutdown signal received")
        cleanup_lock()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


# =========================
# BOT START
# =========================
def start_bot(settings):
    ensure_single_instance()
    setup_signal_handlers()

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    # =========================
    # SAFE TELEGRAM INIT
    # =========================
    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("[INIT] Webhook cleared")

            # flush updates safely
            try:
                await application.bot.get_updates(offset=-1)
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"[POST_INIT ERROR] {e}")

    app.post_init = post_init

    # =========================
    # HANDLERS
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