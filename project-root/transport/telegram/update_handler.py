from typing import Any, Dict, Optional


class TelegramUpdateHandler:
    """
    AI Platform v4.7 — Transport Layer Component

    Responsibility:
    - Normalize Telegram update structure
    - Extract minimal transport-level fields
    - Forward to message router (orchestrator)

    No business logic allowed.
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def extract_message(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts message payload safely from Telegram update.
        """

        if "message" in update:
            return update["message"]

        if "edited_message" in update:
            return update["edited_message"]

        if "callback_query" in update:
            return update["callback_query"]

        return None

    async def handle(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main transport handler entrypoint.

        Only:
        - extracts message
        - passes raw + extracted data to orchestrator
        """

        message = self.extract_message(update)

        # =========================
        # NO LOGIC HERE
        # ONLY DELEGATION
        # =========================
        result = await self.orchestrator.handle_update(
            {
                "raw_update": update,
                "message": message,
            }
        )

        return result