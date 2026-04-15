class SelfCorrection:
    """
    AI evaluates its own output quality
    """

    def reflect(self, input_text: str, output: str):
        score = 0

        if len(output) < 20:
            score -= 2

        if "I don't know" in output:
            score -= 1

        if len(output) > 200:
            score += 1

        return {
            "score": score,
            "needs_improvement": score < 0
        }