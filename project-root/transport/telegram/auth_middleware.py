from __future__ import annotations

from typing import Callable, Awaitable, Any, Dict, Optional

from security.auth import AuthService, AuthContext


# =========================
# TYPE ALIAS
# =========================
Handler = Callable[[Dict[str, Any], AuthContext], Awaitable[Any]]


# =========================
# AUTH MIDDLEWARE
# =========================
class AuthMiddleware:
    """
    ROLE:
    - extract auth token from incoming update
    - verify identity via AuthService
    - attach AuthContext to pipeline

    STRICT RULES:
    - no business logic
    - no payments logic
    - no routing decisions
    - no LLM interaction
    """

    def __init__(self, auth_service: AuthService):
        self._auth = auth_service

    # =========================
    # EXTRACT TOKEN
    # =========================
    def _extract_token(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        Telegram updates may contain auth in different places:
        - message text (e.g. /start token)
        - metadata field (future bot extensions)
        """

        message = payload.get("message", {})
        text = message.get("text", "")

        if isinstance(text, str) and text.startswith("/auth "):
            return text.replace("/auth ", "").strip()

        return None

    # =========================
    # MAIN WRAPPER
    # =========================
    async def __call__(
        self,
        payload: Dict[str, Any],
        handler: Handler,
    ) -> Any:

        token = self._extract_token(payload)

        if not token:
            # anonymous context
            context = AuthContext(
                user_id="anonymous",
                is_authenticated=False,
                roles=[],
                metadata={"auth": "missing"},
            )
            return await handler(payload, context)

        context = self._auth.verify_token(token)

        if context is None:
            # invalid token fallback
            context = AuthContext(
                user_id="anonymous",
                is_authenticated=False,
                roles=[],
                metadata={"auth": "invalid"},
            )

        return await handler(payload, context)