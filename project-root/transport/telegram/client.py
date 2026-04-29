import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"
_MAX_LEN = 4096
_TIMEOUT = 10.0


async def send_typing(chat_id: int) -> None:
    """Show typing indicator. Fire-and-forget."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{_TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
                timeout=5.0,
            )
    except Exception:
        pass  # never block on typing indicator


async def send_message(chat_id: int, text: str) -> None:
    """
    Send message to chat, splitting automatically if > 4096 chars.
    Splits on newline boundary to preserve formatting.
    """
    if not text:
        return

    chunks = _split(text)
    async with httpx.AsyncClient() as client:
        for chunk in chunks:
            try:
                await client.post(
                    f"{_TELEGRAM_API}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": chunk,
                        "parse_mode": "Markdown",
                    },
                    timeout=_TIMEOUT,
                )
            except Exception as exc:
                logger.error("send_message failed", extra={
                    "chat_id": chat_id,
                    "error": str(exc),
                })


async def answer_callback(callback_query_id: str, text: str = "") -> None:
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{_TELEGRAM_API}/answerCallbackQuery",
                json={"callback_query_id": callback_query_id, "text": text},
                timeout=5.0,
            )
    except Exception as exc:
        logger.error("answer_callback failed", extra={"error": str(exc)})


def _split(text: str) -> list[str]:
    """Split text into chunks of max _MAX_LEN chars on newline boundaries."""
    if len(text) <= _MAX_LEN:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= _MAX_LEN:
            chunks.append(text)
            break
        # find last newline within limit
        cut = text.rfind("\n", 0, _MAX_LEN)
        if cut == -1:
            cut = _MAX_LEN
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()

    return [c for c in chunks if c]