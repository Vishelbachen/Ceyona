from __future__ import annotations

from typing import Dict, Any, Callable, Awaitable, Optional


# =========================
# TYPE ALIAS
# =========================
CallbackHandlerFunc = Callable[[Dict[str, Any]], Awaitable[Any]]


# =========================
# CALLBACK HANDLER
# =========================
class CallbackHandler:
    """
    ROLE:
    - handle Telegram callback_query events
    - route UI interactions to update handler layer
    - normalize callback payloads

    STRICT RULES:
    - no business logic
    - no payments logic
    - no LLM calls
    - no authentication decisions
    """

    # =========================
    # ENTRY POINT
    # =========================
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Telegram callback payload entrypoint.
        """

        callback = payload.get("callback_query")

        if not callback:
            return {"status": "ignored", "reason": "no_callback_query"}

        data = self._extract_data(callback)

        normalized = self._normalize(callback, data)

        # just return structured event to upper layer
        return {
            "status": "ok",
            "type": "callback",
            "data": normalized,
        }

    # =========================
    # EXTRACT RAW CALLBACK DATA
    # =========================
    def _extract_data(self, callback: Dict[str, Any]) -> Optional[str]:
        return callback.get("data")

    # =========================
    # NORMALIZATION LAYER
    # =========================
    def _normalize(
        self,
        callback: Dict[str, Any],
        data: Optional[str],
    ) -> Dict[str, Any]:

        message = callback.get("message", {})
        user = callback.get("from", {})

        return {
            "callback_id": callback.get("id"),
            "user_id": user.get("id"),
            "data": data,
            "message_id": message.get("message_id"),
            "chat_id": message.get("chat", {}).get("id"),
        }