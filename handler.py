import logging
from engine.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

orchestrator = Orchestrator()


async def handle_message(user_id: int, text: str) -> str:
    try:
        text = (text or "").strip()

        if not text:
            return "Empty input"

        result = await orchestrator.process(
            user_id=user_id,
            text=text
        )

        return str(result) if result else "No response"

    except Exception as e:
        logger.exception(f"[HANDLER ERROR] {e}")
        return "System error. Try again later."