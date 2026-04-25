from fastapi import APIRouter, Request
import os
import httpx

router = APIRouter()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )


@router.post("/webhook")
async def webhook(request: Request):

    # lazy imports (NO IMPORT TIME SIDE EFFECTS)
    from transport.telegram.message_router import handle_update
    from transport.telegram.middleware import telegram_security_middleware

    update = await request.json()

    signature = request.headers.get("X-Telegram-Signature", "")

    if not await telegram_security_middleware(update, signature):
        return {"ok": True}

    result = await handle_update(update)

    chat_id = update["message"]["chat"]["id"]

    if isinstance(result, dict):

        if "response" in result:
            await send_message(chat_id, str(result["response"]))

        elif result.get("status") == "denied":
            await send_message(chat_id, "⛔ denied")

        elif result.get("status") == "payment_required":
            await send_message(chat_id, "💳 payment required")

    return {"ok": True}