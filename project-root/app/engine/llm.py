import asyncio
import httpx

from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


# -------------------------
# REUSABLE CLIENT (IMPORTANT FOR SCALE)
# -------------------------
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(12.0))

    return _client


# -------------------------
# RESPONSE WRAPPER
# -------------------------
class LLMResponse:
    def __init__(self, content: str):
        self.content = content


# -------------------------
# GROQ CALL
# -------------------------
async def groq_call(model: str, prompt: str, temperature: float = 0.4) -> tuple[str, int]:

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
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }

    client = get_client()

    resp = await client.post(url, headers=headers, json=payload)

    return resp.text, resp.status_code


# -------------------------
# MAIN PIPELINE
# -------------------------
async def run_llm(
    model: str,
    prompt: str,
    retries: int = 2,
    trace_id: str | None = None
) -> LLMResponse:

    last_error = None

    for attempt in range(retries + 1):

        try:
            logger.log(
                "INFO",
                "llm_request",
                trace_id=trace_id,
                model=model,
                attempt=attempt
            )

            # stable temperature (NO drift)
            temp = 0.4

            raw, status = await asyncio.wait_for(
                groq_call(model, prompt, temperature=temp),
                timeout=12
            )

            # -------------------------
            # HTTP HANDLING
            # -------------------------
            if status in (429, 500, 502, 503):

                raise RuntimeError(f"Retryable HTTP {status}")

            if status != 200:
                raise RuntimeError(f"HTTP {status}")

            content = _extract_content(raw)

            cleaned = _sanitize(content)

            if cleaned:
                return LLMResponse(content=cleaned)

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

            await asyncio.sleep(0.4 * (attempt + 1))

    raise LLMError(
        code="LLM_001",
        message=f"All LLM attempts failed: {str(last_error)}",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# SAFE CONTENT PARSER
# -------------------------
def _extract_content(raw: str) -> str:
    try:
        import json
        data = json.loads(raw)
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


# -------------------------
# SANITIZER (SAFE VERSION)
# -------------------------
def _sanitize(text: str) -> str:

    if not text:
        return ""

    text = text.strip()

    if len(text) < 3:
        return ""

    # only remove explicit AI self-identification
    forbidden = [
        "i am an ai",
        "as an ai assistant",
        "я являюсь ии",
        "я — искусственный интеллект"
    ]

    low = text.lower()

    for f in forbidden:
        if f in low:
            return ""

    return text