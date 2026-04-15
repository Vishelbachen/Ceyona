class MemoryRanker:
    """
    Scores memory importance for retrieval optimization
    """

    def score(self, text: str):
        score = 0

        if "important" in text.lower():
            score += 3

        if any(x in text.lower() for x in ["error", "bug", "problem"]):
            score += 2

        if len(text) > 200:
            score += 1

        return score