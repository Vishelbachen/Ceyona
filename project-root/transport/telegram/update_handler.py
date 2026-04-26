from __future__ import annotations

from typing import Dict, Any

from transport.telegram.auth_middleware import AuthMiddleware, AuthContext


# =========================
# UPDATE HANDLER
# =========================
class UpdateHandler:
    """
    ROLE:
    - bridge between transport layer and core execution layer
    - unify message/callback/system updates into single pipeline entry
    - attach auth context via middleware

    STRICT RULES:
    - no business logic
    - no routing decisions
    - no payments logic
    - no LLM calls
    """

    def __init__(self, auth_middleware: AuthMiddleware):
        self._auth = auth_middleware

    # =========================
    # MAIN ENTRYPOINT
    # =========================
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point for all Telegram updates.
        """

        return await self._auth(payload, self._process)

    # =========================
    # CORE BRIDGE FUNCTION
    # =========================
    async def _process(
        self,
        payload: Dict[str, Any],
        context: AuthContext,
    ) -> Dict[str, Any]:
        """
        This is ONLY a bridge to core system.
        """

        # normalize event envelope for core orchestrator
        event = {
            "source": "telegram",
            "type": self._detect_type(payload),
            "payload": payload,
            "auth": {
                "user_id": context.user_id,
                "is_authenticated": context.is_authenticated,
                "roles": context.roles,
                "metadata": context.metadata,
            },
        }

        # here we WOULD call core orchestrator (DI injected in bootstrap)
        # but transport layer must not import core directly
        return {
            "status": "forwarded_to_core",
            "event": event,
        }

    # =========================
    # TYPE DETECTION
    # =========================
    def _detect_type(self, payload: Dict[str, Any]) -> str:

        if "callback_query" in payload:
            return "callback"

        if "message" in payload:
            return "message"

        return "unknown"