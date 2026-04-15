class MultiAgentDebate:
    """
    Agents generate multiple answers and compete
    """

    async def debate(self, models: list, prompt: str):
        responses = []

        for model in models:
            try:
                res = await model.generate(prompt)
                responses.append(res)
            except:
                continue

        return self.select_best(responses)

    def select_best(self, responses: list):
        if not responses:
            return "No response"

        # scoring: longest + most structured wins
        return max(responses, key=lambda x: len(x))