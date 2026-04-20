import asyncio
import json
import time
import httpx

from typing import Optional

from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


# -------------------------
# CLIENT (REUSED)
# -------------------------
_client: Optional[httpx.AsyncClient] = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, read=12.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            )
        )

    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


# -------------------------
# RESPONSE OBJECT
# -------------------------
class LLMResponse:
    def __init__(self, content: str, raw: dict):
        self.content = content
        self.raw = raw


# -------------------------
# GROQ CALL (TRANSPORT)
# -------------------------
async def groq_call(
    model: str,
    prompt: str,
    temperature: float
) -> dict:

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Be precise, structured, and logically consistent."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature
    }

    client = get_client()

    resp = await client.post(url, headers=headers, json=payload)

    # retryable errors
    if resp.status_code in (429, 500, 502, 503):
        raise RuntimeError(f"Retryable HTTP {resp.status_code}")

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    try:
        return resp.json()
    except Exception:
        raise RuntimeError("Invalid JSON response from LLM")


# -------------------------
# MAIN PIPELINE
# -------------------------
async def run_llm(
    model: str,
    prompt: str,
    retries: int = 2,
    trace_id: Optional[str] = None
) -> LLMResponse:

    last_error = None

    for attempt in range(retries + 1):

        start = time.time()

        try:
            logger.log(
                "INFO",
                "llm_request",
                trace_id=trace_id,
                model=model,
                attempt=attempt
            )

            data = await asyncio.wait_for(
                groq_call(model, prompt, temperature=0.4),
                timeout=15
            )

            content = _extract_content(data)

            cleaned = _sanitize(content)

            if not cleaned:
                raise RuntimeError("Empty or invalid LLM response")

            latency = round(time.time() - start, 3)

            logger.log(
                "INFO",
                "llm_success",
                trace_id=trace_id,
                model=model,
                latency=latency,
                response_size=len(cleaned)
            )

            return LLMResponse(content=cleaned, raw=data)

        except Exception as e:
            last_error = e

            logger.log(
                "ERROR",
                "llm_error",
                trace_id=trace_id,
                model=model,
                attempt=attempt,
                error=str(e)
            )

            # retry only if safe
            if "Retryable" not in str(e) and attempt >= retries:
                break

            await asyncio.sleep(0.4 * (attempt + 1))

    raise LLMError(
        code="LLM_001",
        message=f"All LLM attempts failed: {str(last_error)}",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# SAFE PARSER
# -------------------------
def _extract_content(data: dict) -> str:
    try:
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
    except Exception:
        return ""


# -------------------------
# SAFE SANITIZER
# -------------------------
def _sanitize(text: str) -> str:

    if not text:
        return ""

    text = text.strip()

    if len(text) < 3:
        return ""

    forbidden = [
        "i am an ai",
        "as an ai assistant",
        "я являюсь ии",
        "я — искусственный интеллект"
    ]

    for f in forbidden:
        text = text.replace(f, "").replace(f.capitalize(), "")

    return text.strip()