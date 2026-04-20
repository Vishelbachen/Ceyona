from fastapi import APIRouter, Request
from uuid import uuid4

from app.core.logger import logger
from app.core.orchestrator import handle_request
from app.contracts.message import OrchestratorRequest, UserMessage
from app.core.response_handler import ResponseHandler

router = APIRouter()


# -------------------------
# TELEGRAM WEBHOOK
# -------------------------
@router.post("/webhook")
async def telegram_webhook(request: Request):

    trace_id = str(uuid4())

    try:
        payload = await request.json()

        parsed = _parse_telegram(payload, trace_id)

        if not parsed:
            return {"ok": True, "trace_id": trace_id}

        logger.log("INFO", "webhook_received", trace_id=trace_id)

        req = OrchestratorRequest(
            trace_id=trace_id,
            user_message=UserMessage(
                user_id=parsed["user_id"],
                text=parsed["text"]
            )
        )

        result = await handle_request(req)

        await ResponseHandler.handle(
            response=result,
            chat_id=parsed["chat_id"]
        )

        logger.log("INFO", "webhook_success", trace_id=trace_id)

        return {"ok": True, "trace_id": trace_id}

    except Exception as e:
        logger.log("ERROR", "webhook_crash", trace_id=trace_id, error=str(e))

        return {"ok": False, "trace_id": trace_id}


# -------------------------
# PARSER LAYER
# -------------------------
def _parse_telegram(payload: dict, trace_id: str) -> dict | None:
    """
    Isolated parsing layer (no business logic)
    """

    message = payload.get("message") or {}

    text = message.get("text")
    if not text:
        logger.log("INFO", "empty_text_skipped", trace_id=trace_id)
        return None

    user = message.get("from") or {}
    chat = message.get("chat") or {}

    user_id = str(user.get("id") or "unknown")
    chat_id = chat.get("id")

    if not chat_id:
        logger.log("ERROR", "missing_chat_id", trace_id=trace_id)
        return None

    return {
        "text": text,
        "user_id": user_id,
        "chat_id": chat_id
    }