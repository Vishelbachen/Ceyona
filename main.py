import asyncio
import logging

from bot import start_bot
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ceyona")


async def main():
    settings = Settings()

    logger.info("Ceyona AI system starting...")

    await start_bot(settings)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutdown complete")