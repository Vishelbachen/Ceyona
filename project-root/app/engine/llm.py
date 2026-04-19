import asyncio
from app.core.logger import logger
from app.core.errors import LLMError
from app.config import settings  # ✅ подключили


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


async def fake_groq_call(model: str, prompt: str) -> str:
    await asyncio.sleep(0.3)

    if prompt is None:
        return "ERROR: empty prompt"

    return f"[{model}] {prompt}"


async def run_llm(model: str, prompt: str, retries: int = 2, trace_id: str = None):
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

            # 🔥 В БУДУЩЕМ:
            # settings.GROQ_API_KEY будет использоваться здесь

            response = await asyncio.wait_for(
                fake_groq_call(model, str(prompt)),
                timeout=5
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