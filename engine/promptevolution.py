class PromptEvolution:
    """
    AI improves its own prompting strategy
    """

    def evolve(self, base_prompt: str, score: float):
        if score > 0.8:
            return base_prompt + "\nBe more concise."

        if score < 0.3:
            return base_prompt + "\nBe more detailed and structured."

        return base_prompt