class ToolRouter:
    """
    Decides REAL execution tool (not just intent)
    """

    def route(self, text: str) -> dict:
        t = (text or "").lower()

        # ======================
        # WEATHER TOOL
        # ======================
        if any(x in t for x in ["weather", "погода", "температура"]):
            return {
                "tool": "weather",
                "args": self._extract_city(t)
            }

        # ======================
        # MAPS TOOL
        # ======================
        if any(x in t for x in ["route", "map", "где", "как доехать", "distance"]):
            return {
                "tool": "maps",
                "args": self._extract_location(t)
            }

        # ======================
        # SEARCH TOOL
        # ======================
        if any(x in t for x in ["search", "найди", "find", "что такое"]):
            return {
                "tool": "search",
                "args": t
            }

        # ======================
        # NO TOOL → LLM
        # ======================
        return {
            "tool": "llm",
            "args": text
        }

    # ----------------------
    # SIMPLE EXTRACTION (SAFE)
    # ----------------------
    def _extract_city(self, text: str) -> str:
        words = text.split()

        blacklist = {"weather", "погода", "какая", "сегодня", "now", "today"}

        for w in words:
            if w not in blacklist and len(w) > 2:
                return w

        return "Tbilisi"

    def _extract_location(self, text: str) -> str:
        return text