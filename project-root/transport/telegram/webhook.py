from fastapi import APIRouter, Request
from app.bootstrap import get_container

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    container = get_container()

    try:
        # =========================
        # SAFE JSON PARSE
        # =========================
        try:
            update = await request.json()
        except Exception:
            return {"status": "ignored", "reason": "invalid json"}

        if not update:
            return {"status": "ignored", "reason": "empty payload"}

        # =========================
        # ORCHESTRATOR
        # =========================
        try:
            result = await container.orchestrator.handle_update(update)
        except Exception as e:
            return {
                "status": "orchestrator_error",
                "error": str(e),
            }

        # =========================
        # TELEGRAM OUTBOUND (FIXED NAME)
        # =========================
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if chat_id:
            await container.telegram_client.send_message(
                chat_id=chat_id,
                text=str(result.get("result", "")),
            )

        return {"status": "ok"}

    except Exception as e:
        return {
            "status": "fatal_error",
            "message": str(e),
        }