import logging
from engine.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

orchestrator = Orchestrator()


async def handle_message(user_id: int, text: str) -> str:
    try:
        if not text or not text.strip():
            return "Empty input received."

        result = await orchestrator.process(
            user_id=user_id,
            text=text.strip()
        )

        return result

    except Exception as e:
        logger.exception(f"[Handler] Error: {e}")
        return "System error. Please try again."