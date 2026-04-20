from app.engine.telegram import send_message
from app.core.logger import logger
from app.core.response_formatter import ResponseFormatter


class ResponseHandler:
    """
    Production-safe response delivery layer.

    Responsibilities:
    - format response safely
    - guarantee Telegram delivery attempt
    - never crash orchestrator
    """

    # -------------------------
    # SAFE SEND LAYER
    # -------------------------
    @staticmethod
    async def send_text(text: str, chat_id: str, trace_id: str):

        safe_text = (text or "").strip()

        if not safe_text:
            safe_text = "⚠️ Empty response"

        try:
            logger.log(
                "INFO",
                "telegram_send_start",
                trace_id=trace_id,
                chat_id=chat_id
            )

            await send_message(
                chat_id=chat_id,
                text=safe_text,
                trace_id=trace_id
            )

            logger.log(
                "INFO",
                "telegram_send_success",
                trace_id=trace_id
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "telegram_send_failed",
                trace_id=trace_id,
                error=str(e)
            )

            # IMPORTANT: do not propagate
            return

    # -------------------------
    # MAIN ENTRY POINT
    # -------------------------
    @staticmethod
    async def handle(response, chat_id: str):

        if response is None:
            logger.log(
                "ERROR",
                "null_response",
                trace_id="missing_trace"
            )
            return

        trace_id = getattr(response, "trace_id", None) or "missing_trace"

        logger.log(
            "INFO",
            "response_handler_start",
            trace_id=trace_id
        )

        try:
            # -------------------------
            # FORMATTER (SAFE WRAP)
            # -------------------------
            try:
                formatted_text = ResponseFormatter.format(response)
            except Exception as e:
                logger.log(
                    "ERROR",
                    "formatter_failed",
                    trace_id=trace_id,
                    error=str(e)
                )
                formatted_text = "⚠️ Formatter error"

            # -------------------------
            # TYPE SAFETY
            # -------------------------
            if not isinstance(formatted_text, str):
                formatted_text = str(formatted_text)

            formatted_text = formatted_text.strip()

            if not formatted_text:
                logger.log(
                    "WARN",
                    "empty_formatted_response",
                    trace_id=trace_id
                )
                formatted_text = "⚠️ No valid response generated"

            # -------------------------
            # DELIVERY
            # -------------------------
            await ResponseHandler.send_text(
                text=formatted_text,
                chat_id=chat_id,
                trace_id=trace_id
            )

            logger.log(
                "INFO",
                "response_handler_done",
                trace_id=trace_id
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "response_handler_failed",
                trace_id=trace_id,
                error=str(e)
            )

            # NEVER crash webhook pipeline
            return