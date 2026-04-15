import logging
from engine.orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Singleton (IMPORTANT for memory + performance)
orchestrator = Orchestrator()


# =========================
# MESSAGE HANDLER
# =========================
async def handle_message(user_id: int, text: str) -> str:
    try:
        if not text:
            return "Empty input received."

        text = text.strip()

        if len(text) == 0:
            return "Empty input received."

        logger.info(f"[HANDLER] user_id={user_id} | text={text}")

        result = await orchestrator.process(
            user_id=user_id,
            text=text
        )

        if result is None:
            logger.warning("[HANDLER] Orchestrator returned None")
            return "No response generated."

        return str(result)

    except Exception as e:
        logger.exception(f"[HANDLER] Critical error: {e}")
        return "System error. Please try again later."