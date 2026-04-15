import logging
import signal
import sys

from bot import start_bot
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ceyona")


def handle_exit(signum, frame):
    logger.info("Shutdown signal received")
    sys.exit(0)


def main():
    settings = Settings()

    logger.info("Ceyona AI system starting...")

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    try:
        start_bot(settings)
    except Exception as e:
        logger.exception(f"[MAIN ERROR] {e}")
        raise


if __name__ == "__main__":
    main()