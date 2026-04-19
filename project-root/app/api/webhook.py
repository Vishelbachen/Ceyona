from fastapi import APIRouter, Request
from uuid import uuid4

from app.contracts.message import OrchestratorRequest, UserMessage
from app.core.orchestrator import handle_request
from app.core.response_handler import ResponseHandler
from app.core.logger import logger

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    trace_id = str(uuid4())

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

        if not chat_id:
            return {"ok": False, "error": "missing_chat_id"}

        req = OrchestratorRequest(
            trace_id=trace_id,
            user_id=user_id,
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        result = await handle_request(req)

        await ResponseHandler.handle(
            response=result,
            chat_id=chat_id
        )

        return {"ok": True, "trace_id": trace_id}

    except Exception as e:
        logger.log("ERROR", "webhook_crash", trace_id=trace_id, error=str(e))

        return {"ok": False, "error": str(e), "trace_id": trace_id}