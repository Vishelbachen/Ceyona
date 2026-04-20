import httpx
import asyncio

from app.config.settings import settings
from app.core.logger import logger


# -------------------------
# HTTP CLIENT (REUSED)
# -------------------------
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        _client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(10.0)
        )

    return _client


# -------------------------
# CORE SENDER
# -------------------------
async def send_message(chat_id: str | int, text: str, trace_id: str | None = None):

    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    client = get_client()

    max_retries = 2

    for attempt in range(max_retries + 1):

        try:
            logger.log(
                "INFO",
                "telegram_send_attempt",
                trace_id=trace_id,
                attempt=attempt
            )

            response = await client.post(url, json=payload)

            # -------------------------
            # HTTP ERROR CLASSIFICATION
            # -------------------------
            if response.status_code >= 500:
                raise RuntimeError("Telegram server error")

            if response.status_code == 400:
                # ❌ do NOT retry bad request
                logger.log(
                    "ERROR",
                    "telegram_bad_request",
                    trace_id=trace_id,
                    body=response.text
                )
                return

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")

            data = response.json()

            if not data.get("ok"):
                logger.log(
                    "ERROR",
                    "telegram_api_failed",
                    trace_id=trace_id,
                    response=data
                )
                return

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

            if attempt < max_retries:
                await asyncio.sleep(0.4 * (attempt + 1))
            else:
                logger.log(
                    "CRITICAL",
                    "telegram_send_failed_final",
                    trace_id=trace_id
                )
                return