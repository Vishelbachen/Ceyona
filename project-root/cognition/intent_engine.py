class IntentEngine:
    """
    Detects user intent from raw input
    """

    def detect(self, text: str) -> str:
        text = text.lower()

        if "?" in text:
            return "question"
        if "create" in text or "build" in text:
            return "generation"
        if "error" in text:
            return "debug"
        return "general"