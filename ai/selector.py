import asyncio

from ai.groq import GroqClient
from ai.openai import OpenAIClient
from ai.mistral import MistralClient
from ai.gemini import GeminiClient


class AISelector:
    def __init__(self, settings):
        self.groq = GroqClient(settings)
        self.openai = OpenAIClient(settings)
        self.mistral = MistralClient(settings)
        self.gemini = GeminiClient(settings)

    async def generate(self, prompt: str, route: dict) -> str:
        model_type = route.get("type", "general")

        # приоритет моделей
        if model_type == "fast":
            order = [self.groq, self.mistral, self.openai]

        elif model_type == "analysis":
            order = [self.gemini, self.openai, self.mistral]

        else:
            order = [self.groq, self.openai, self.mistral, self.gemini]

        for model in order:
            try:
                result = await model.generate(prompt)
                if result:
                    return result
            except Exception:
                continue

        return "Ceyona AI: All models failed."