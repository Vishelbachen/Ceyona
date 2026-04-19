import httpx
from app.config import settings


async def send_message(chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text
        })