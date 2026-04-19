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

        # 📩 SAFE PARSING
        message = payload.get("message") or {}
        text = message.get("text")

        user = message.get("from") or {}
        user_id = str(user.get("id") or "unknown")

        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        # 🧯 SAFETY CHECKS
        if not text:
            logger.log("INFO", "empty_text_skipped", trace_id=trace_id)
            return {"ok": True, "trace_id": trace_id}

        if not chat_id:
            logger.log("ERROR", "missing_chat_id", trace_id=trace_id)
            return {"ok": False, "error": "missing_chat_id", "trace_id": trace_id}

        logger.log("INFO", "webhook_received", trace_id=trace_id)

        # 🧠 BUILD ORCHESTRATOR REQUEST
        req = OrchestratorRequest(
            trace_id=trace_id,
            user_id=user_id,
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        # 🔁 CORE EXECUTION
        result = await handle_request(req)

        logger.log(
            "INFO",
            "orchestrator_result_received",
            trace_id=trace_id,
            success=getattr(result, "success", None)
        )

        # 📤 RESPONSE LAYER
        try:
            await ResponseHandler.handle(
                response=result,
                chat_id=chat_id
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "response_handler_failed",
                trace_id=trace_id,
                error=str(e)
            )

            return {
                "ok": False,
                "error": "response_handler_failed",
                "trace_id": trace_id
            }

        logger.log("INFO", "webhook_success", trace_id=trace_id)

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
            "error": str(e),
            "trace_id": trace_id
        }