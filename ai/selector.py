class ModelSelector:
    def select(self, route: str, user_input: str):
        if route == "coding":
            from ai.openai import OpenAIModel
            return OpenAIModel()

        if route == "fast":
            from ai.groq import GroqModel
            return GroqModel()

        if route == "creative":
            from ai.mistral import MistralModel
            return MistralModel()

        from ai.gemini import GeminiModel
        return GeminiModel()