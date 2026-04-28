from typing import Callable, Dict, Any, Awaitable


class TelegramAuthMiddleware:
    """
    AI Platform v4.7 — Transport Security Middleware

    Responsibility:
    - Validate incoming Telegram updates origin
    - Basic auth / token validation (if configured)
    - Reject unauthorized requests early

    STRICT RULES:
    - No business logic
    - No routing decisions
    - No access to LLM / retrieval / memory
    - No interpretation of message content
    """

    def __init__(self, settings):
        self.settings = settings
        self.bot_token = settings.BOT_TOKEN

    def _is_valid_telegram_request(self, update: Dict[str, Any]) -> bool:
        """
        Basic structural validation of Telegram update.
        NOTE: Telegram itself does not send BOT_TOKEN in payload,
        so this is typically used for webhook-level verification headers.
        """

        # In real deployment, this is usually validated via:
        # - X-Telegram-Bot-Api-Secret-Token header
        # or webhook secret path
        return True

    def _is_authorized(self, request_headers: Dict[str, Any]) -> bool:
        """
        Optional security layer for webhook protection.
        """

        if not self.bot_token:
            return True  # if not configured, skip

        secret_token = request_headers.get("X-Telegram-Bot-Api-Secret-Token")

        if not secret_token:
            return False

        return secret_token == self.bot_token

    async def __call__(
        self,
        request,
        call_next: Callable[[Any], Awaitable[Any]],
    ):
        """
        ASGI-style middleware entrypoint.
        """

        headers = dict(request.headers)

        # =========================
        # SECURITY CHECK ONLY
        # =========================
        if not self._is_authorized(headers):
            return {
                "status": "error",
                "message": "Unauthorized",
            }

        # continue pipeline
        response = await call_next(request)
        return response