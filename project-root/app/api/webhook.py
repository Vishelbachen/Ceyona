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

        # 🧯 SAFETY CHECKS
        if not text:
            logger.log("INFO", "empty_text_skipped", trace_id=trace_id)
            return {"ok": True}

        if not chat_id:
            logger.log("ERROR", "missing_chat_id", trace_id=trace_id)
            return {"ok": False, "error": "missing_chat_id"}

        logger.log("INFO", "webhook_received", trace_id=trace_id)

        # 🧠 BUILD REQUEST (🔥 ВАЖНО: user_id внутри)
        req = OrchestratorRequest(
            trace_id=trace_id,
            user_id=user_id,  # ✅ ФИКС ТВОЕЙ ОШИБКИ
            user_message=UserMessage(
                user_id=user_id,
                text=text
            )
        )

        result = await handle_request(req)

        logger.log(
            "INFO",
            "orchestrator_result_received",
            trace_id=trace_id,
            success=getattr(result, "success", None)
        )

        try:
            handler_result = ResponseHandler.handle(
                response=result,
                chat_id=chat_id
            )

            if handler_result is not None:
                await handler_result

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