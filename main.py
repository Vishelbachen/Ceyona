import logging
import signal

from bot import start_bot
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ceyona")


def main():
    settings = Settings()

    logger.info("Ceyona AI system starting...")

    try:
        start_bot(settings)
    except Exception as e:
        logger.exception(f"[MAIN] Fatal error: {e}")


if __name__ == "__main__":
    main()