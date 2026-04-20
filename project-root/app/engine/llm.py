import asyncio
from openai import AsyncOpenAI

from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


# -------------------------
# CORE CALL
# -------------------------

async def groq_call(model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Follow instructions strictly. Respond in user language."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content


# -------------------------
# MAIN PIPELINE
# -------------------------

async def run_llm(
    model: str,
    prompt: str,
    retries: int = 2,
    trace_id: str | None = None
) -> LLMResponse:

    attempt = 0

    while attempt <= retries:
        try:
            logger.log("INFO", "llm_request", trace_id=trace_id, model=model, attempt=attempt)

            response = await asyncio.wait_for(
                groq_call(model, prompt),
                timeout=12
            )

            cleaned = _sanitize(response)

            if not cleaned:
                raise ValueError("Empty response")

            logger.log("INFO", "llm_response", trace_id=trace_id, model=model)

            return LLMResponse(content=cleaned)

        except Exception as e:
            logger.log("ERROR", "llm_error", trace_id=trace_id, error=str(e))

        attempt += 1

    raise LLMError(
        code="LLM_001",
        message="LLM failed after retries",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# SANITIZER
# -------------------------

def _sanitize(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    blocked = (
        "i am an ai",
        "as an ai",
        "я являюсь ии",
        "assistant model"
    )

    lower = text.lower()

    if any(b in lower for b in blocked):
        return ""

    return text