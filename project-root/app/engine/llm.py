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
    """
    Clean Groq execution layer.
    No prompt logic here.
    """

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.6,  # чуть стабильнее (важно для reasoning)
    )

    return response.choices[0].message.content or ""


# -------------------------
# MAIN PIPELINE
# -------------------------

async def run_llm(
    model: str,
    prompt: str,
    retries: int = 2,
    timeout: int = 12,
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

            response = await asyncio.wait_for(
                groq_call(model, prompt),
                timeout=timeout
            )

            cleaned = _sanitize_llm_output(response)

            if not cleaned:
                raise ValueError("Empty LLM response")

            logger.log(
                "INFO",
                "llm_response",
                trace_id=trace_id,
                model=model
            )

            return LLMResponse(content=cleaned)

        except asyncio.TimeoutError as e:
            last_error = e
            logger.log(
                "ERROR",
                "llm_timeout",
                trace_id=trace_id,
                model=model,
                attempt=attempt
            )

            await asyncio.sleep(0.2 * (attempt + 1))  # backoff

        except Exception as e:
            last_error = e
            logger.log(
                "ERROR",
                "llm_error",
                trace_id=trace_id,
                model=model,
                error=str(e),
                attempt=attempt
            )

            await asyncio.sleep(0.1)

    raise LLMError(
        code="LLM_001",
        message=f"All LLM retries failed: {last_error}",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# 🧠 SANITIZER (SAFE + NON-BREAKING)
# -------------------------

def _sanitize_llm_output(text: str) -> str:
    """
    Safety layer:
    - prevents broken outputs
    - does NOT over-filter reasoning content
    """

    if not text:
        return ""

    text = text.strip()

    if len(text) < 2:
        return ""

    # мягкая защита (НЕ ломает reasoning)
    dangerous_fragments = [
        "assistant model",
        "system prompt",
        "openai policy"
    ]

    lowered = text.lower()

    for frag in dangerous_fragments:
        if frag in lowered:
            text = lowered.replace(frag, "").strip()

    return text