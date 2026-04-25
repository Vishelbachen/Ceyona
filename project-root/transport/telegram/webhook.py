from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhook")
async def webhook(request: Request):

    # lazy import (CRITICAL FIX)
    from transport.telegram.message_router import handle_update
    from transport.telegram.middleware import telegram_security_middleware

    update = await request.json()

    signature = request.headers.get("X-Telegram-Signature", "")

    if not await telegram_security_middleware(update, signature):
        return {"error": "unauthorized"}

    return await handle_update(update)