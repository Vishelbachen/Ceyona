import logging

logger = logging.getLogger(__name__)

# SAFE IMPORTS (prevents crash)
try:
    from ai.groq import GroqClient
    from ai.openai import OpenAIClient
    from ai.mistral import MistralClient
    from ai.gemini import GeminiClient
except Exception as e:
    logger.warning(f"[AI IMPORT FAIL SAFE] {e}")

    GroqClient = None
    OpenAIClient = None
    MistralClient = None
    GeminiClient = None


class AISelector:
    def __init__(self, settings):
        self.settings = settings

        self.groq = GroqClient(settings) if GroqClient else None
        self.openai = OpenAIClient(settings) if OpenAIClient else None
        self.mistral = MistralClient(settings) if MistralClient else None
        self.gemini = GeminiClient(settings) if GeminiClient else None

        self.models = [m for m in [
            self.groq,
            self.openai,
            self.mistral,
            self.gemini
        ] if m is not None]

    def select_order(self, model_type: str):
        if model_type == "fast":
            return self.models[:3]

        if model_type == "analysis":
            return list(reversed(self.models))

        if model_type == "coding":
            return self.models[::-1]

        return self.models

    async def generate(self, prompt: str, route: dict) -> str:
        model_type = route.get("type", "general")
        order = self.select_order(model_type)

        last_error = None

        for model in order:
            try:
                result = await model.generate(prompt)

                if isinstance(result, str) and result.strip():
                    return result.strip()

            except Exception as e:
                last_error = e
                continue

        logger.error(f"[AISelector FAIL]: {last_error}")
        return None