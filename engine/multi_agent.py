class MultiAgent:
    """
    Runs multiple models and votes for best answer
    """

    async def run(self, models: list, prompt: str):
        responses = []

        for model in models:
            try:
                res = await model.generate(prompt)
                responses.append(res)
            except:
                continue

        return self.vote(responses)

    def vote(self, responses: list):
        if not responses:
            return "No response generated"

        # simple consensus logic (can be upgraded later)
        return max(responses, key=len)