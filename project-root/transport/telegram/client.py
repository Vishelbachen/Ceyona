from typing import Optional, Dict, Any
import httpx


class TelegramClient:
    """
    AI Platform v4.7 — Telegram Transport Client

    RESPONSIBILITY:
    - Send messages to Telegram API
    - No business logic
    - No orchestration
    - No decision-making

    RULES:
    - Pure I/O adapter
    - Stateless
    - Safe failure handling
    """

    def __init__(self, bot_token: str, timeout: float = 10.0):
        if not bot_token:
            raise ValueError("BOT_TOKEN is required for TelegramClient")

        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.timeout = timeout

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat.
        """

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if extra:
            payload.update(extra)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json=payload,
            )

        # safe return (no crash propagation)
        try:
            return response.json()
        except Exception:
            return {
                "ok": False,
                "error": "Invalid Telegram response",
                "status_code": response.status_code,
            }

    async def send_typing_action(self, chat_id: int) -> None:
        """
        Optional UX improvement: show 'typing...' in Telegram.
        """

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await client.post(
                f"{self.base_url}/sendChatAction",
                json={
                    "chat_id": chat_id,
                    "action": "typing",
                },
            )