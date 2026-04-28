class FastAgent:
    """
    Fast response agent (low latency)
    """

    def run(self, query: str) -> str:
        return f"[FAST AGENT] quick answer for: {query}"