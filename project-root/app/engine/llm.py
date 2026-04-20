import asyncio
from openai import AsyncOpenAI

from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


# -------------------------
# CLIENT
# -------------------------
client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)


# -------------------------
# RESPONSE WRAPPER
# -------------------------
class LLMResponse:
    def __init__(self, content: str):
        self.content = content


# -------------------------
# CORE CALL
# -------------------------
async def groq_call(model: str, prompt: str, temperature: float = 0.5) -> str:

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Follow instructions strictly. "
                    "Be precise, structured, and consistent."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
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

            # -------------------------
            # ADAPTIVE TEMPERATURE STRATEGY
            # -------------------------
            temp = 0.5 if attempt == 0 else 0.7

            response = await asyncio.wait_for(
                groq_call(model, prompt, temperature=temp),
                timeout=12
            )

            cleaned = _sanitize(response)

            if cleaned:
                logger.log(
                    "INFO",
                    "llm_success",
                    trace_id=trace_id,
                    model=model,
                    attempt=attempt
                )

                return LLMResponse(content=cleaned)

            logger.log(
                "WARN",
                "empty_or_invalid_response",
                trace_id=trace_id,
                attempt=attempt
            )

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

            await asyncio.sleep(0.3 * (attempt + 1))  # backoff

    raise LLMError(
        code="LLM_001",
        message=f"All LLM attempts failed: {str(last_error)}",
        layer="llm",
        trace_id=trace_id
    )


# -------------------------
# SANITIZER (IMPROVED)
# -------------------------
def _sanitize(text: str) -> str:

    if not text:
        return ""

    text = text.strip()

    if len(text) < 2:
        return ""

    low = text.lower()

    blacklist_phrases = (
        "i am an ai",
        "as an ai",
        "я — искусственный интеллект",
        "я являюсь ии",
        "assistant model",
        "language model"
    )

    # soft filtering (don’t overkill response)
    if any(b in low for b in blacklist_phrases):
        return ""

    return text