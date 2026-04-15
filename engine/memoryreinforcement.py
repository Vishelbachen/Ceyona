class MemoryReinforcement:
    """
    Strengthens important memories over time
    """

    def reinforce(self, memory_score: int):
        if memory_score > 5:
            return "strong"
        elif memory_score > 2:
            return "medium"
        return "weak"