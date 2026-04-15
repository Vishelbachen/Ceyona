class ScoreEngine:
    def evaluate(self, output: str):
        score = 0

        if len(output) > 50:
            score += 1

        if any(x in output.lower() for x in ["because", "therefore", "so"]):
            score += 1

        if "." in output:
            score += 1

        return score