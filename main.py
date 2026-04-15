import asyncio
import logging

from bot import start_bot
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    try:
        settings = Settings()
        logger.info("Starting Ceyona AI system...")
        await start_bot(settings)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())