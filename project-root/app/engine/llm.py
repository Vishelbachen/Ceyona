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
    Groq API call (clean architecture)
    PromptBuilder handles system logic
    """

    response = await client.chat.completions.create(
        model=model,
        messages=[
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
            logger.log(
                "INFO",
                "llm_request",
                trace_id=trace_id,
                model=model,
                attempt=attempt
            )

            response = await asyncio.wait_for(
                groq_call(model, prompt),
                timeout=10
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

        except asyncio.TimeoutError:
            logger.log(
                "ERROR",
                "llm_timeout",
                trace_id=trace_id,
                model=model
            )

        except Exception as e:
            logger.log(
                "ERROR",
                "llm_error",
                trace_id=trace_id,
                model=model,
                error=str(e)
            )

        attempt += 1

    raise LLMError(
        code="LLM_001",
        message="All LLM retries failed",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# 🧠 SANITIZER (SAFE VERSION)
# -------------------------

def _sanitize_llm_output(text: str) -> str:
    """
    Only cleans:
    - broken outputs
    - obvious identity leaks (soft, not destructive)
    """

    if not text:
        return ""

    text = text.strip()

    lowered = text.lower()

    soft_blocks = [
        "assistant model",
        "system prompt"
    ]

    # ⚠️ soft filter (NOT destructive)
    if any(b in lowered for b in soft_blocks):
        text = text.replace("assistant model", "").strip()

    return text