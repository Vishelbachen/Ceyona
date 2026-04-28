class ReasoningEngine:
    """
    Minimal reasoning layer (pre-LLM shaping)
    """

    def reason(self, intent: str, query: str) -> str:
        if intent == "question":
            return f"Analyze and answer: {query}"
        if intent == "generation":
            return f"Generate structured output for: {query}"
        if intent == "debug":
            return f"Diagnose issue: {query}"
        return query