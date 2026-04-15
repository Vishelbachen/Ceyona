class ModelSelector:
    def select(self, route: str, user_input: str, context: dict = None):
        context = context or {}

        length = len(user_input)

        # FAST MODE (cheap + quick)
        if context.get("fast_mode"):
            from ai.groq import GroqModel
            return GroqModel()

        # LONG / COMPLEX → GPT
        if length > 500 or route == "coding":
            from ai.openai import OpenAIModel
            return OpenAIModel()

        # CREATIVE / BALANCED
        if route in ["knowledge", "general"]:
            from ai.gemini import GeminiModel
            return GeminiModel()

        # DEFAULT
        from ai.mistral import MistralModel
        return MistralModel()