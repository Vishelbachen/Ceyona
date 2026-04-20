import asyncio
from openai import AsyncOpenAI

from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


# -------------------------
# CLIENT INIT (GROQ COMPAT OPENAI SDK)
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
# CORE API CALL
# -------------------------

async def _call_llm_api(model: str, prompt: str) -> str:
    """
    Single raw LLM call.
    No mutation, no filtering, no business logic.
    """

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Follow the instructions in the user message strictly. "
                    "Respond in the same language as the user. "
                    "Do not include unnecessary prefaces."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
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

            response_text = await asyncio.wait_for(
                _call_llm_api(model, prompt),
                timeout=timeout
            )

            if not response_text or not response_text.strip():
                raise ValueError("Empty LLM response")

            logger.log(
                "INFO",
                "llm_response",
                trace_id=trace_id,
                model=model
            )

            return LLMResponse(content=response_text.strip())

        except asyncio.TimeoutError as e:
            last_error = e
            logger.log(
                "ERROR",
                "llm_timeout",
                trace_id=trace_id,
                model=model,
                attempt=attempt
            )

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

    raise LLMError(
        code="LLM_001",
        message=f"LLM failed after retries: {str(last_error)}",
        layer="llm",
        trace_id=trace_id
    )