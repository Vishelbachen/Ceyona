from typing import Any, Dict


class TelegramCallbackHandler:
    """
    AI Platform v4.7 — Transport Layer Callback Handler

    Responsibility:
    - Receive Telegram callback_query updates
    - Normalize callback payload
    - Forward to orchestrator

    STRICT RULES:
    - No business logic
    - No intent parsing
    - No routing decisions
    - No LLM / retrieval / memory access
    """

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def _extract_callback_data(self, update: Dict[str, Any]) -> str:
        """
        Safely extracts callback data from Telegram update.
        """

        callback = update.get("callback_query", {})
        return callback.get("data", "") if callback else ""

    async def handle(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint for callback updates.
        """

        callback_data = self._extract_callback_data(update)

        callback_query = update.get("callback_query", {})

        # =========================
        # PURE DELEGATION ONLY
        # =========================
        result = await self.orchestrator.handle_update(
            {
                "raw_update": update,
                "callback_query": callback_query,
                "callback_data": callback_data,
                "type": "callback",
            }
        )

        return result