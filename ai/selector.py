import asyncio


class AISelector:
    def __init__(self, settings):
        self.groq = GroqClient(settings)
        self.openai = OpenAIClient(settings)
        self.mistral = MistralClient(settings)
        self.gemini = GeminiClient(settings)

    def select_order(self, model_type: str):
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

                if isinstance(result, str) and result.strip():
                    return result.strip()

            except Exception as e:
                last_error = e
                continue

        # 🔥 CRITICAL FIX: NEVER return debug to user
        return None