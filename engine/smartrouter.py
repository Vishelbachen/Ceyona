class SmartRouter:
    """
    Production-grade model selection (OpenAI-style routing layer)
    """

    def select(self, route: str, length: int, load: float, complexity: float):

        if load > 0.85:
            return "groq"

        if complexity > 0.8:
            return "openai"

        if route == "coding":
            return "openai"

        if route == "knowledge":
            return "gemini"

        if length < 200:
            return "mistral"

        return "groq"