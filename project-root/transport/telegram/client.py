from __future__ import annotations

from typing import Optional, Dict, Any
import httpx


class TelegramClient:
    """
    AI Platform v4.7 — Telegram Transport Client

    RESPONSIBILITY:
    - ONLY outbound communication to Telegram API
    - NO business logic
    - NO orchestration
    - NO interpretation of messages

    RULE:
    This is a pure I/O adapter (HTTP client wrapper).
    """

    def __init__(self, bot_token: str):
        if not bot_token:
            raise ValueError("BOT_TOKEN is required for TelegramClient")

        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        self._client = httpx.AsyncClient(timeout=10.0)

    # =========================
    # CORE METHOD
    # =========================
    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send message to Telegram chat.

        STRICT:
        - no formatting logic
        - no fallback logic
        - no retries (handled externally if needed)
        """

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        if extra:
            payload.update(extra)

        response = await self._client.post(
            f"{self.base_url}/sendMessage",
            json=payload,
        )

        response.raise_for_status()
        return response.json()

    # =========================
    # OPTIONAL CLEANUP
    # =========================
    async def close(self):
        """
        Graceful shutdown of HTTP client.
        """
        await self._client.aclose()