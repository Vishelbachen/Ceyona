import httpx
import asyncio

from app.config.settings import settings
from app.core.logger import logger


# -------------------------
# CONFIG CHECK
# -------------------------
if not settings.BOT_TOKEN:
    raise RuntimeError("[CONFIG ERROR] BOT_TOKEN is missing")


BASE_URL = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"


# -------------------------
# CORE SENDER
# -------------------------
async def send_message(chat_id: str, text: str, trace_id: str | None = None):
    """
    Resilient Telegram transport layer.

    Features:
    - retry logic
    - status validation
    - timeout safety
    - structured logging
    """

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    max_retries = 2

    async with httpx.AsyncClient(
        http2=True,
        timeout=10.0
    ) as client:

        for attempt in range(max_retries + 1):

            try:
                logger.log(
                    "INFO",
                    "telegram_send_attempt",
                    trace_id=trace_id,
                    attempt=attempt,
                    chat_id=chat_id
                )

                response = await client.post(BASE_URL, json=payload)

                # -------------------------
                # HTTP VALIDATION
                # -------------------------
                if response.status_code != 200:
                    logger.log(
                        "ERROR",
                        "telegram_http_error",
                        trace_id=trace_id,
                        status_code=response.status_code,
                        body=response.text
                    )

                    raise RuntimeError("Telegram API error")

                data = response.json()

                if not data.get("ok"):
                    logger.log(
                        "ERROR",
                        "telegram_api_failed",
                        trace_id=trace_id,
                        response=data
                    )

                    raise RuntimeError("Telegram API returned not ok")

                # -------------------------
                # SUCCESS
                # -------------------------
                logger.log(
                    "INFO",
                    "telegram_send_success",
                    trace_id=trace_id
                )

                return

            except Exception as e:
                logger.log(
                    "ERROR",
                    "telegram_send_error",
                    trace_id=trace_id,
                    error=str(e),
                    attempt=attempt
                )

                # retry delay (simple backoff)
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))

                else:
                    logger.log(
                        "CRITICAL",
                        "telegram_send_failed_final",
                        trace_id=trace_id
                    )
                    return