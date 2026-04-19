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
            await send_message(chat_id=chat_id, text=text)

            logger.log(
                "INFO",
                "response_sent",
                trace_id=trace_id,
                transport="telegram"
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "response_failed",
                trace_id=trace_id,
                error=str(e)
            )