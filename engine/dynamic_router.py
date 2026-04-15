class DynamicRouter:
    """
    Chooses model based on:
    - cost
    - latency
    - complexity
    - system load
    """

    def select(self, route: str, length: int, load: float):

        if load > 0.8:
            return "groq"

        if route == "coding" or length > 800:
            return "openai"

        if route == "knowledge":
            return "gemini"

        return "mistral"