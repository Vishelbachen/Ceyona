class ToolRouter:
    """
    Maps user input → конкретный инструмент
    (НЕ принимает решение, а только выбирает tool)
    """

    def route(self, user_input: str):
        text = user_input.lower()

        if any(x in text for x in ["weather", "temperature", "rain", "forecast"]):
            return {"tool": "weather", "confidence": 0.95}

        if any(x in text for x in ["search", "google", "find", "look up"]):
            return {"tool": "search", "confidence": 0.9}

        if any(x in text for x in ["map", "location", "route", "near"]):
            return {"tool": "maps", "confidence": 0.9}

        if any(x in text for x in ["price", "cost", "crypto", "ton", "wallet"]):
            return {"tool": "analytics", "confidence": 0.85}

        return None