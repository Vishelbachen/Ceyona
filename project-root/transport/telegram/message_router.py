from typing import Any, Dict


class TelegramMessageRouter:
    """
    AI Platform v4.7 — Transport Layer Router

    Responsibility:
    - Receive normalized Telegram update
    - Extract routing-safe payload
    - Forward to core orchestrator

    STRICT RULES:
    - No LLM calls
    - No retrieval calls
    - No memory access
    - No decision-making logic
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def _extract_text(self, message: Dict[str, Any]) -> str:
        """
        Extracts user text safely from Telegram message object.
        """

        if not message:
            return ""

        return (
            message.get("text")
            or message.get("caption")
            or ""
        )

    async def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main routing entrypoint.

        payload format:
        {
            "raw_update": {...},
            "message": {...}
        }
        """

        raw_update = payload.get("raw_update", {})
        message = payload.get("message", {})

        text = self._extract_text(message)

        # =========================
        # PURE DELEGATION
        # NO DECISIONS HERE
        # =========================
        result = await self.orchestrator.handle_update(
            {
                "raw_update": raw_update,
                "message": message,
                "text": text,
            }
        )

        return result