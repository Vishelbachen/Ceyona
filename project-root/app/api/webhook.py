from fastapi import APIRouter, Request
from uuid import uuid4

from app.contracts.message import OrchestratorRequest, UserMessage
from app.core.orchestrator import handle_request
from app.core.response_handler import ResponseHandler

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        payload = await request.json()

        message = payload.get("message", {})
        text = message.get("text")

        user = message.get("from", {})
        user_id = str(user.get("id", "unknown"))

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not text:
            return {"ok": True}

        trace_id = str(uuid4())

        req = OrchestratorRequest(
            trace_id=trace_id,
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        result = await handle_request(req)

        # 🔥 ВАЖНО: теперь через handler
        await ResponseHandler.handle(
            response=result,
            chat_id=chat_id
        )

        return {
            "ok": True,
            "trace_id": trace_id
        }

    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }