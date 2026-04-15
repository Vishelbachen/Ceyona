class MemoryRanker:
    """
    Scores memory importance for long-term AI memory
    """

    def score(self, text: str):
        score = 0

        text_lower = text.lower()

        # critical signals
        if any(x in text_lower for x in ["error", "bug", "fail"]):
            score += 3

        if any(x in text_lower for x in ["important", "remember"]):
            score += 4

        if any(x in text_lower for x in ["user prefers", "user likes"]):
            score += 5

        if len(text) > 300:
            score += 1

        return score