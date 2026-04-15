import re


class Router:
    """
    COMPAT LAYER (Orchestrator expects Router)
    Wraps ToolRouter internally
    """

    def __init__(self):
        self.tool_router = ToolRouter()

    def route(self, text: str) -> dict:
        tool_result = self.tool_router.route(text)

        # normalize output for orchestrator
        return {
            "type": tool_result.get("tool", "llm"),
            "args": tool_result.get("args"),
            "confidence": tool_result.get("confidence", 0.5)
        }


class ToolRouter:
    """
    PRO TOOL ROUTER v3
    - deterministic
    - safe extraction
    - confidence scoring
    """

    def route(self, text: str) -> dict:
        t = (text or "").lower()

        # WEATHER
        if any(x in t for x in ["weather", "погода", "температура"]):
            return {
                "tool": "weather",
                "args": self._extract_city(t),
                "confidence": 0.95
            }

        # MAPS / ROUTE
        if any(x in t for x in ["route", "map", "где", "как доехать", "distance", "from", "to"]):
            return {
                "tool": "maps",
                "args": self._extract_location(t),
                "confidence": 0.90
            }

        # SEARCH
        if any(x in t for x in ["search", "найди", "find", "что такое", "who is"]):
            return {
                "tool": "search",
                "args": t,
                "confidence": 0.80
            }

        # DEFAULT
        return {
            "tool": "llm",
            "args": text,
            "confidence": 0.50
        }

    def _extract_city(self, text: str) -> str:
        words = re.split(r"\s+", text)

        blacklist = {
            "weather", "погода", "today", "now",
            "сегодня", "какая", "температура"
        }

        candidates = [
            w.strip(",.")
            for w in words
            if w not in blacklist and len(w) > 2
        ]

        return candidates[-1] if candidates else "Tbilisi"

    def _extract_location(self, text: str) -> str:
        return text.strip()