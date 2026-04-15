import logging
from engine.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

orchestrator = Orchestrator()


async def handle_message(user_id: int, text: str) -> str:
    try:
        if text is None:
            return "Empty input received."

        text = text.strip()

        if not text:
            return "Empty input received."

        logger.info(f"[Handler] user_id={user_id} input received")

        result = await orchestrator.process(
            user_id=user_id,
            text=text
        )

        if not result:
            return "No response generated."

        return result

    except Exception as e:
        logger.exception(f"[Handler] Error: {e}")
        return "System error. Please try again later."