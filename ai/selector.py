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

    def select_order(self, model_type: str):
        """
        Deterministic routing strategy
        """

        if model_type == "fast":
            return [self.groq, self.mistral, self.openai]

        if model_type == "analysis":
            return [self.gemini, self.openai, self.mistral]

        if model_type == "coding":
            return [self.openai, self.gemini, self.mistral]

        return [self.groq, self.openai, self.mistral, self.gemini]

    async def generate(self, prompt: str, route: dict) -> str:
        model_type = route.get("type", "general")
        order = self.select_order(model_type)

        last_error = None

        for model in order:
            try:
                result = await model.generate(prompt)

                if result and isinstance(result, str):
                    return result

            except Exception as e:
                last_error = e
                continue

        return f"Ceyona AI: All models failed. ({last_error})"