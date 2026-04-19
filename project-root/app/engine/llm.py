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


def extract_user_input(prompt: str) -> str:
    if "USER INPUT:" in prompt:
        return prompt.split("USER INPUT:")[-1].strip()
    return prompt


async def groq_call(model: str, prompt: str) -> str:
    """
    Real Groq API call
    """

    user_input = extract_user_input(prompt)

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": user_input}
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content


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

            logger.log(
                "INFO",
                "llm_response",
                trace_id=trace_id,
                model=model
            )

            return LLMResponse(content=response)

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