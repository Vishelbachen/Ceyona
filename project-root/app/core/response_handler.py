from app.engine.telegram import send_message
from app.core.logger import logger


class ResponseHandler:

    @staticmethod
    async def send_text(
        text: str,
        chat_id: str,
        trace_id: str
    ):
        try:
            logger.log(
                "INFO",
                "sending_telegram_message",
                trace_id=trace_id,
                chat_id=chat_id
            )

            result = await send_message(chat_id=chat_id, text=text)

            logger.log(
                "INFO",
                "response_sent",
                trace_id=trace_id,
                transport="telegram",
                result=str(result)
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "response_failed",
                trace_id=trace_id,
                error=str(e),
                chat_id=chat_id
            )

            # 🔥 ВАЖНО: НЕ ГЛОТАЕМ ТИХО
            raise


    @staticmethod
    async def handle(
        response,
        chat_id: str
    ):
        try:
            trace_id = getattr(response, "trace_id", "unknown")

            # 🧯 SAFE SUCCESS CHECK
            success = getattr(response, "success", False)

            if success:
                text = getattr(response, "data", "")
                if not text:
                    text = "⚠️ Empty response"

            else:
                error = getattr(response, "error", {}) or {}
                message = error.get("message", "Unknown error")

                text = f"⚠️ Error: {message}"

            logger.log(
                "INFO",
                "response_handler_start",
                trace_id=trace_id
            )

            await ResponseHandler.send_text(
                text=text,
                chat_id=chat_id,
                trace_id=trace_id
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "response_handler_failed",
                trace_id=getattr(response, "trace_id", "unknown"),
                error=str(e)
            )

            # 🔥 КРИТИЧЕСКИ ВАЖНО: пробрасываем дальше (чтобы видеть в webhook)
            raise