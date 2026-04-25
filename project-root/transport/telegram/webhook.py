from fastapi import APIRouter, Request
import os
import httpx
import sys
import traceback

router = APIRouter()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()


async def send_message(chat_id: int, text: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text}
            )
            log(f"SEND STATUS {r.status_code}: {r.text}")
    except Exception:
        log("SEND MESSAGE ERROR:")
        traceback.print_exc()


@router.post("/webhook")
async def webhook(request: Request):

    log("🔥 WEBHOOK HIT")

    from transport.telegram.message_router import handle_update
    from transport.telegram.middleware import telegram_security_middleware

    try:
        update = await request.json()
    except Exception:
        log("JSON PARSE ERROR")
        traceback.print_exc()
        return {"ok": True}

    log(f"UPDATE: {update}")

    signature = request.headers.get("X-Telegram-Signature", "")

    try:
        ok = await telegram_security_middleware(update, signature)
        log(f"SECURITY RESULT: {ok}")
        if not ok:
            return {"ok": True}
    except Exception:
        log("SECURITY ERROR")
        traceback.print_exc()

    try:
        result = await handle_update(update)
        log(f"RESULT: {result}")
    except Exception:
        log("HANDLE_UPDATE CRASH")
        traceback.print_exc()
        return {"ok": True}

    try:
        chat_id = update["message"]["chat"]["id"]

        if isinstance(result, dict):
            if "response" in result:
                await send_message(chat_id, str(result["response"]))

            elif result.get("status") == "denied":
                await send_message(chat_id, "⛔ denied")

            elif result.get("status") == "payment_required":
                await send_message(chat_id, "💳 payment required")

    except Exception:
        log("SEND FLOW ERROR")
        traceback.print_exc()

    return {"ok": True}