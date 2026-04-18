import asyncio
from app.core.logger import logger


class LLMError(Exception):
    pass


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


async def fake_groq_call(model: str, prompt: str) -> str:
    await asyncio.sleep(0.3)
    return f"[{model}] {prompt}"


async def run_llm(model: str, prompt: str, retries: int = 2):
    attempt = 0

    while attempt <= retries:
        try:
            logger.log("INFO", "llm_request", model=model, attempt=attempt)

            response = await asyncio.wait_for(
                fake_groq_call(model, prompt),
                timeout=5
            )

            logger.log("INFO", "llm_response", model=model)

            return LLMResponse(content=response)

        except asyncio.TimeoutError:
            logger.log("ERROR", "llm_timeout", model=model)

        except Exception as e:
            logger.log("ERROR", "llm_error", model=model, error=str(e))

        attempt += 1

    raise LLMError("All LLM retries failed")