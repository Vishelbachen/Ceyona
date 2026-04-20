import httpx
import asyncio

from typing import Optional, List

from app.config.settings import settings
from app.core.logger import logger


# -------------------------
# CLIENT (REUSED)
# -------------------------
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        _client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(10.0)
        )

    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


# -------------------------
# PUBLIC API
# -------------------------
async def send_message(
    chat_id: str | int,
    text: str,
    trace_id: Optional[str] = None,
    parse_mode: str = "Markdown"
):
    """
    Safe message sender with:
    - retry
    - rate limit handling
    - message splitting
    """

    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    parts = _split_message(text)

    for part in parts:
        await _send_single(
            chat_id=chat_id,
            text=part,
            trace_id=trace_id,
            parse_mode=parse_mode
        )


# -------------------------
# INTERNAL: SINGLE SEND
# -------------------------
async def _send_single(
    chat_id: str | int,
    text: str,
    trace_id: Optional[str],
    parse_mode: str
):

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }

    client = get_client()
    max_retries = 3

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
            # RATE LIMIT (CRITICAL)
            # -------------------------
            if response.status_code == 429:
                retry_after = _extract_retry_after(response)

                logger.log(
                    "WARNING",
                    "telegram_rate_limited",
                    trace_id=trace_id,
                    retry_after=retry_after
                )

                await asyncio.sleep(retry_after or 1.5)
                continue

            # -------------------------
            # SERVER ERROR
            # -------------------------
            if response.status_code >= 500:
                raise RuntimeError("Telegram server error")

            # -------------------------
            # BAD REQUEST (NO RETRY)
            # -------------------------
            if response.status_code == 400:
                logger.log(
                    "ERROR",
                    "telegram_bad_request",
                    trace_id=trace_id,
                    body=response.text
                )
                return

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")

            data = _safe_json(response)

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
                await asyncio.sleep(0.5 * (attempt + 1))
            else:
                logger.log(
                    "CRITICAL",
                    "telegram_send_failed_final",
                    trace_id=trace_id
                )
                return


# -------------------------
# UTIL: SAFE JSON
# -------------------------
def _safe_json(response: httpx.Response) -> dict:
    try:
        return response.json()
    except Exception:
        return {}


# -------------------------
# UTIL: RETRY AFTER
# -------------------------
def _extract_retry_after(response: httpx.Response) -> float:
    try:
        data = response.json()
        return float(data.get("parameters", {}).get("retry_after", 1))
    except Exception:
        return 1.0


# -------------------------
# UTIL: MESSAGE SPLIT
# -------------------------
def _split_message(text: str, limit: int = 4096) -> List[str]:
    """
    Telegram message limit = 4096 chars
    """
    if not text:
        return [""]

    if len(text) <= limit:
        return [text]

    parts = []

    while text:
        part = text[:limit]
        parts.append(part)
        text = text[limit:]

    return parts