from fastapi import APIRouter, Request
from app.bootstrap import get_container

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    AI Platform v4.7 — Telegram Inbound Adapter

    RESPONSIBILITY:
    - receive Telegram update
    - validate input shape
    - delegate to orchestrator
    - send response back via Telegram client

    STRICT RULES:
    - no business logic
    - no parsing decisions
    - no routing decisions
    """

    container = get_container()

    # =========================
    # SAFE JSON PARSING
    # =========================
    try:
        update = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    if not update:
        return {"status": "ignored", "reason": "empty_payload"}

    # =========================
    # EXECUTION PIPELINE
    # =========================
    try:
        result = await container.orchestrator.handle_update(update)
    except Exception as e:
        # IMPORTANT: isolate orchestrator crashes from HTTP layer
        return {
            "status": "orchestrator_error",
            "error": str(e),
        }

    # =========================
    # TELEGRAM RESPONSE
    # =========================
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if chat_id:
        await container.telegram_client.send_message(
            chat_id=chat_id,
            text=str(result.get("result", "")),
        )

    # =========================
    # ACK TO TELEGRAM
    # =========================
    return {
        "status": "ok",
        "processed": True,
    }