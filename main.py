import logging
import os
import signal
import sys
import threading

from bot import start_bot
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ceyona")

LOCK_FILE = "/tmp/ceyona_bot.lock"


def create_lock():
    if os.path.exists(LOCK_FILE):
        logger.error("Bot already running (lock exists). Exiting.")
        sys.exit(1)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def remove_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception as e:
        logger.warning(f"Lock cleanup failed: {e}")


def handle_exit(signum, frame):
    logger.info("Shutdown signal received")
    remove_lock()
    sys.exit(0)


def main():
    settings = Settings()

    logger.info("Ceyona AI system starting...")

    # 🔥 CRITICAL: prevent double instance
    create_lock()

    # graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        start_bot(settings)
    except Exception as e:
        logger.exception(f"[MAIN] Fatal error: {e}")
    finally:
        remove_lock()


if __name__ == "__main__":
    main()