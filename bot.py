import logging
import os
import asyncio
import signal

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handler import handle_message

logger = logging.getLogger(__name__)

# =========================
# SINGLE INSTANCE LOCK
# =========================
LOCK_FILE = "/tmp/ceyona_bot.lock"


def ensure_single_instance():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())

            # check process exists
            os.kill(old_pid, 0)

            raise RuntimeError("Bot already running (active instance detected)")

        except ProcessLookupError:
            logger.warning("[LOCK] stale lock removed")
            os.remove(LOCK_FILE)

        except Exception:
            logger.warning("[LOCK] corrupted lock removed")
            try:
                os.remove(LOCK_FILE)
            except:
                pass

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
        await update.message.reply_text("System error. Try again.")


# =========================
# SIGNALS
# =========================
def setup_signals():
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
    setup_signals()

    app = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    async def post_init(application):
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("[INIT] Webhook cleared")

            try:
                await application.bot.get_updates(offset=-1)
            except:
                pass

        except Exception as e:
            logger.warning(f"[POST_INIT ERROR] {e}")

    app.post_init = post_init

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    logger.info("BOT STARTED (PRO MODE - SINGLE INSTANCE SAFE)")

    try:
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )
    finally:
        cleanup_lock()