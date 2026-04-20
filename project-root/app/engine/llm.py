import asyncio
from openai import AsyncOpenAI
from app.config.settings import settings
from app.core.logger import logger
from app.core.errors import LLMError


client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


async def groq_call(model: str, prompt: str) -> str:
    res = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Follow instructions strictly."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
    )
    return res.choices[0].message.content


async def run_llm(model: str, prompt: str, trace_id: str | None = None, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            logger.log("INFO", "llm_request", trace_id=trace_id, model=model)

            raw = await asyncio.wait_for(
                groq_call(model, prompt),
                timeout=12
            )

            raw = _clean(raw)

            if not raw:
                raise ValueError("empty response")

            return LLMResponse(raw)

        except Exception as e:
            logger.log("ERROR", "llm_error", trace_id=trace_id, error=str(e))

    raise LLMError("LLM failed")


def _clean(text: str) -> str:
    if not text:
        return ""
    return text.strip()