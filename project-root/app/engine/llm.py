import asyncio
from app.core.logger import logger
from app.core.errors import LLMError
from app.config.settings import settings


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


def extract_user_input(prompt: str) -> str:
    """
    Extracts USER INPUT from PromptBuilder format
    """
    if "USER INPUT:" in prompt:
        return prompt.split("USER INPUT:")[-1].strip()
    return prompt


async def fake_groq_call(model: str, prompt: str) -> str:
    """
    Smart Mock LLM (simulates real model behavior)
    """

    await asyncio.sleep(0.3)

    if not prompt:
        return "Ошибка: пустой запрос"

    user_text = extract_user_input(prompt).lower()

    # 🔥 Простая "интеллектуальная" логика
    if any(word in user_text for word in ["привет", "здравствуйте", "хай"]):
        return "Привет! 😊 Чем могу помочь?"

    if "как дела" in user_text:
        return "Всё отлично! Готов помочь тебе 🚀"

    if "кто ты" in user_text:
        return "Я ИИ-ассистент, который работает через модульную архитектуру 😎"

    if "помоги" in user_text:
        return "Конечно! Опиши задачу подробнее — разберёмся вместе."

    if "код" in user_text or "программ" in user_text:
        return "Давай разберём код. Пришли часть или опиши проблему."

    # fallback (универсальный ответ)
    return "Я понял твой запрос. Сейчас я бы подключил настоящую модель и дал точный ответ 😉"


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
