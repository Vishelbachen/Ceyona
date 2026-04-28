class SafetyAgent:
    """
    Safety filtering / validation agent
    """

    def validate(self, query: str) -> bool:
        forbidden = ["hack", "exploit", "steal"]
        return not any(word in query.lower() for word in forbidden)