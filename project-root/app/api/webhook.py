from fastapi import APIRouter, Request
from uuid import uuid4
from typing import Optional, Dict, Any

from app.core.logger import logger
from app.core.orchestrator import handle_request
from app.contracts.message import OrchestratorRequest, UserMessage

router = APIRouter()


# -------------------------
# ENTRYPOINT
# -------------------------
@router.post("/webhook")
async def telegram_webhook(request: Request):

    trace_id = str(uuid4())

    try:
        payload: Dict[str, Any] = await request.json()

        if not isinstance(payload, dict):
            return {"ok": True, "trace_id": trace_id}

        parsed = _parse_telegram(payload)

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

        # -------------------------
        # CORE CALL (ISOLATED)
        # -------------------------
        result = await handle_request(req)

        logger.log("INFO", "webhook_success", trace_id=trace_id)

        # ❗ IMPORTANT:
        # webhook returns only ACK
        # NO RESPONSE DELIVERY HERE
        return {
            "ok": True,
            "trace_id": trace_id
        }

    except Exception as e:

        logger.log(
            "ERROR",
            "webhook_crash",
            trace_id=trace_id,
            error=str(e)
        )

        return {
            "ok": False,
            "trace_id": trace_id
        }


# -------------------------
# TELEGRAM PARSER (SAFE)
# -------------------------
def _parse_telegram(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    message = payload.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not text or not isinstance(text, str):
        return None

    user = message.get("from") or {}
    chat = message.get("chat") or {}

    user_id = user.get("id")
    chat_id = chat.get("id")

    if not user_id or not chat_id:
        return None

    return {
        "text": text.strip(),
        "user_id": str(user_id),
        "chat_id": chat_id
    }