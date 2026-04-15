class ToolRouter:
    """
    ToolRouter = decides external system execution ONLY
    (NOT reasoning, NOT intent)
    """

    def route(self, user_input: str, route: str = None):
        text = user_input.lower()

        # =========================
        # WEATHER SYSTEM
        # =========================
        if any(x in text for x in ["weather", "temperature", "rain", "forecast"]):
            return {
                "tool": "weather",
                "confidence": 0.95
            }

        # =========================
        # SEARCH SYSTEM
        # =========================
        if any(x in text for x in ["search", "google", "find", "look up"]):
            return {
                "tool": "search",
                "confidence": 0.9
            }

        # =========================
        # MAPS / GEO SYSTEM
        # =========================
        if any(x in text for x in ["map", "location", "route", "distance", "near"]):
            return {
                "tool": "maps",
                "confidence": 0.9
            }

        # =========================
        # ANALYTICS / CRYPTO / TON
        # =========================
        if any(x in text for x in ["price", "cost", "crypto", "ton", "wallet"]):
            return {
                "tool": "analytics",
                "confidence": 0.85
            }

        # =========================
        # NO TOOL NEEDED
        # =========================
        return None