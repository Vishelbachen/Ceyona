class CostOptimizer:
    """
    Selects model based on cost + load + complexity
    """

    def select(self, route: str, length: int, fast_mode: bool = False):

        # ultra cheap mode
        if fast_mode:
            return "groq"

        # heavy reasoning
        if route == "coding" or length > 800:
            return "openai"

        # balanced
        if route in ["knowledge", "general"]:
            return "gemini"

        # fallback cheap
        return "mistral"