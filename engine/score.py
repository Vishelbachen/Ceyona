class Scorer:
    def evaluate(self, response: str) -> dict:
        length = len(response)

        return {
            "length": length,
            "quality": "high" if length > 20 else "low"
        }