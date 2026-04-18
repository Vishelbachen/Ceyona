from fastapi import APIRouter, Request
from app.contracts.message import OrchestratorRequest, UserMessage
from app.core.orchestrator import handle_request

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()

        message = payload.get("message", {})
        text = message.get("text")

        user = message.get("from", {})
        user_id = str(user.get("id", "unknown"))

        if not text:
            return {"ok": True}

        req = OrchestratorRequest(
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        result = await handle_request(req)

        return {
            "ok": True,
            "result": result
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }