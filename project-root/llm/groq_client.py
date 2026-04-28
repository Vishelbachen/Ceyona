from dataclasses import dataclass

from groq import AsyncGroq

from app.settings import settings


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class GroqClient:
    def __init__(self) -> None:
        self._client = AsyncGroq(api_key=settings.groq_api_key)

    async def complete(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 1200,
        temperature: float = 0.7,
    ) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            model=response.model,
        )


# Singleton
groq_client = GroqClient()