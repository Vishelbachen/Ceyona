from fastapi import APIRouter, Request, HTTPException
from app.bootstrap import get_container

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()

        if not update:
            raise HTTPException(status_code=400, detail="Empty payload")

        container = get_container()

        result = await container.orchestrator.handle_update(update)

        # =========================
        # EXTRACT TELEGRAM DATA
        # =========================
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = str(result.get("result", ""))

        # =========================
        # OUTBOUND RESPONSE (CRITICAL FIX)
        # =========================
        await container.telegram_client.send_message(
            chat_id=chat_id,
            text=text,
        )

        return {
            "status": "ok",
            "processed": True,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }