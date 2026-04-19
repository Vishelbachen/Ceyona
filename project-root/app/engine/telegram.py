import httpx
from app.config.settings import settings


async def send_message(chat_id: str, text: str):
    """
    Telegram transport layer.
    Pure HTTP client. No business logic.
    """

    if not settings.BOT_TOKEN:
        raise RuntimeError("[CONFIG ERROR] BOT_TOKEN is missing")

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text
        })