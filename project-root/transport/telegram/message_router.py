from __future__ import annotations

from typing import Dict, Any

from transport.telegram.update_handler import UpdateHandler


# =========================
# MESSAGE ROUTER
# =========================
class MessageRouter:
    """
    ROLE:
    - route raw Telegram updates to correct handler
    - normalize entrypoint between message / callback / system events

    STRICT RULES:
    - no business logic
    - no authentication logic
    - no payments logic
    - no LLM calls
    """

    def __init__(self, update_handler: UpdateHandler):
        self._update_handler = update_handler

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    async def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Central routing entry for Telegram updates.
        """

        # callback queries go elsewhere
        if "callback_query" in payload:
            return {
                "status": "forwarded",
                "type": "callback",
            }

        # message-based updates
        if "message" in payload:
            return await self._handle_message(payload)

        # unknown update type
        return {
            "status": "ignored",
            "reason": "unsupported_update_type",
        }

    # =========================
    # MESSAGE HANDLING
    # =========================
    async def _handle_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Forward message payload to domain ingestion layer.
        """

        await self._update_handler.handle(payload)

        return {
            "status": "ok",
            "type": "message",
        }