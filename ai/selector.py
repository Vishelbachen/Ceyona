from ai.openai import OpenAIModel
from ai.gemini import GeminiModel
from ai.groq import GroqModel
from ai.mistral import MistralModel


class ModelSelector:
    """
    Smart cost + performance routing layer
    """

    def select(self, route: str, user_input: str, context: dict = None):
        context = context or {}

        length = len(user_input)

        # =========================
        # FAST MODE (lowest cost)
        # =========================
        if context.get("fast_mode"):
            return GroqModel()

        # =========================
        # CODING / LOGIC HEAVY
        # =========================
        if route == "coding":
            return OpenAIModel()

        # =========================
        # COMPLEX LONG INPUT
        # =========================
        if length > 800:
            return OpenAIModel()

        # =========================
        # DEFAULT BALANCED
        # =========================
        if route in ["knowledge", "general"]:
            return GeminiModel()

        # =========================
        # FALLBACK CHEAP
        # =========================
        return MistralModel()