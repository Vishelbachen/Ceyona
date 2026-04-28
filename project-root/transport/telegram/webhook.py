from fastapi import APIRouter, Request
from app.bootstrap import get_container

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    AI Platform v4.7 — Telegram Inbound Adapter
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
    # 🔥 DEBUG: RAW TELEGRAM UPDATE
    # =========================
    print("RAW UPDATE:", update)

    # =========================
    # EXECUTION PIPELINE
    # =========================
    try:
        result = await container.orchestrator.handle_update(update)
    except Exception as e:
        # isolate crash from HTTP layer
        print("ORCHESTRATOR ERROR:", str(e))
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
        try:
            await container.telegram_client.send_message(
                chat_id=chat_id,
                text=str(result.get("result", "")),
            )
        except Exception as e:
            print("TELEGRAM SEND ERROR:", str(e))

    # =========================
    # ACK
    # =========================
    return {
        "status": "ok",
        "processed": True,
    }