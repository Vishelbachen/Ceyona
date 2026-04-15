import logging

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

    start_bot(settings)


if __name__ == "__main__":
    main()