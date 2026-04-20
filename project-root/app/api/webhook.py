from fastapi import APIRouter, Request
from uuid import uuid4
from typing import Optional, Dict, Any

from app.core.logger import logger
from app.core.orchestrator import handle_request
from app.contracts.message import OrchestratorRequest, UserMessage
from app.core.response_handler import ResponseHandler

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request):

    trace_id = str(uuid4())

    try:
        payload: Dict[str, Any] = await request.json() or {}

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


def _parse_telegram(payload: Dict[str, Any], trace_id: str) -> Optional[Dict[str, Any]]:

    message = payload.get("message") or {}
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not text:
        return None

    user = message.get("from") or {}
    chat = message.get("chat") or {}

    user_id = str(user.get("id") or "unknown")
    chat_id = chat.get("id")

    if chat_id is None:
        return None

    return {
        "text": text,
        "user_id": user_id,
        "chat_id": chat_id
    }