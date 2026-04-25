from fastapi import APIRouter, Request
import os
import httpx

router = APIRouter()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔥 SAFETY CHECK (CRITICAL FIX)
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment variables")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(chat_id: int, text: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text
                }
            )
            print("SEND MESSAGE STATUS:", r.status_code, r.text)
    except Exception as e:
        print("SEND MESSAGE ERROR:", e)


@router.post("/webhook")
async def webhook(request: Request):

    from transport.telegram.message_router import handle_update
    from transport.telegram.middleware import telegram_security_middleware

    try:
        update = await request.json()
    except Exception as e:
        print("JSON PARSE ERROR:", e)
        return {"ok": True}

    print("UPDATE RECEIVED:", update)

    signature = request.headers.get("X-Telegram-Signature", "")

    try:
        if not await telegram_security_middleware(update, signature):
            print("SECURITY BLOCK")
            return {"ok": True}
    except Exception as e:
        print("SECURITY ERROR:", e)

    try:
        result = await handle_update(update)
    except Exception as e:
        print("HANDLE_UPDATE ERROR:", e)
        return {"ok": True}

    print("HANDLE RESULT:", result)

    if isinstance(result, dict) and "chat_id" in result:
        await send_message(result["chat_id"], result["text"])

    return {"ok": True}