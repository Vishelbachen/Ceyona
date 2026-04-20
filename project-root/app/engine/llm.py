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


async def groq_call(model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Follow instructions strictly. Be accurate and structured."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )

    return response.choices[0].message.content


async def run_llm(
    model: str,
    prompt: str,
    retries: int = 2,
    trace_id: str | None = None
) -> LLMResponse:

    for attempt in range(retries + 1):
        try:
            logger.log("INFO", "llm_request", trace_id=trace_id, model=model, attempt=attempt)

            response = await asyncio.wait_for(
                groq_call(model, prompt),
                timeout=12
            )

            cleaned = _sanitize(response)

            if cleaned:
                return LLMResponse(content=cleaned)

        except Exception as e:
            logger.log("ERROR", "llm_error", trace_id=trace_id, error=str(e))

    raise LLMError(
        code="LLM_001",
        message="All LLM attempts failed",
        layer="llm",
        trace_id=trace_id
    )


def _sanitize(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    blacklist = (
        "i am an ai",
        "as an ai",
        "я — искусственный интеллект",
        "assistant model"
    )

    low = text.lower()

    if any(b in low for b in blacklist):
        return ""

    return text