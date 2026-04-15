class SelfCorrection:
    """
    AI evaluates and slightly improves output quality
    (light-weight correction layer for orchestrator)
    """

    def reflect(self, input_text: str, output: str):
        score = 0

        if not output:
            score -= 3

        if len(output) < 20:
            score -= 2

        if "I don't know" in output.lower():
            score -= 1

        if len(output) > 200:
            score += 1

        return {
            "score": score,
            "needs_improvement": score < 0
        }

    async def correct(self, user_input: str, output: str, model=None):
        """
        Orchestrator compatibility method
        (currently lightweight pass-through, upgrade later)
        """
        # future: rewrite / critique / refine loop
        return output