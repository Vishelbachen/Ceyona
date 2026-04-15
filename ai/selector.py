class ModelSelector:
    def select(self, route: str, user_input: str, context: dict = None):
        context = context or {}

        # приоритет скорости
        if context.get("fast"):
            from ai.groq import GroqModel
            return GroqModel()

        # код
        if route == "coding":
            from ai.openai import OpenAIModel
            return OpenAIModel()

        # сложные запросы
        if len(user_input) > 300:
            from ai.openai import OpenAIModel
            return OpenAIModel()

        # дефолт баланс
        from ai.gemini import GeminiModel
        return GeminiModel()