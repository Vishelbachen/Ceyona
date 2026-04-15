import re
import logging

logger = logging.getLogger(__name__)


class ToolRouter:
    def route(self, text: str) -> dict:
        t = (text or "").lower().strip()

        if not t:
            return self._fallback(text)

        # WEATHER
        if any(x in t for x in ["weather", "погода", "температура"]):
            return {
                "tool": "weather",
                "args": self._extract_city(t),
                "confidence": 0.97
            }

        # MAPS
        if any(x in t for x in [
            "route", "map", "где", "как доехать",
            "distance", "from", "to"
        ]):
            return {
                "tool": "maps",
                "args": self._extract_location(t),
                "confidence": 0.92
            }

        # SEARCH
        if any(x in t for x in [
            "search", "найди", "find",
            "who is", "что такое", "кто такой"
        ]):
            return {
                "tool": "search",
                "args": t,
                "confidence": 0.85
            }

        return {
            "tool": "llm",
            "args": text,
            "confidence": 0.5
        }

    def _extract_city(self, text: str) -> str:
        blacklist = {"weather", "погода", "today", "now", "температура"}

        words = re.split(r"\s+", text)

        for w in reversed(words):
            clean = w.strip(",.")
            if clean and clean not in blacklist:
                return clean.capitalize()

        return "Tbilisi"

    def _extract_location(self, text: str) -> str:
        return text.strip()

    def _fallback(self, text: str):
        return {
            "tool": "llm",
            "args": text,
            "confidence": 0.0
        }


class Router:
    """
    COMPAT LAYER (Orchestrator-safe)
    """

    def __init__(self):
        self.tool_router = ToolRouter()

    def route(self, text: str) -> dict:
        try:
            r = self.tool_router.route(text)

            return {
                "type": r.get("tool", "llm"),
                "args": r.get("args"),
                "confidence": float(r.get("confidence", 0.5))
            }

        except Exception as e:
            logger.warning(f"[ROUTER FAILSAFE] {e}")
            return {
                "type": "llm",
                "args": text,
                "confidence": 0.0
            }