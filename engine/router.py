import re
import logging

logger = logging.getLogger(__name__)


# =========================
# TOOL ROUTER (CORE ENGINE)
# =========================
class ToolRouter:
    """
    PRO TOOL ROUTER v3
    - deterministic
    - safe extraction
    - production stable
    """

    def route(self, text: str) -> dict:
        t = (text or "").lower().strip()

        # ======================
        # WEATHER
        # ======================
        if any(x in t for x in ["weather", "погода", "температура"]):
            return {
                "tool": "weather",
                "args": self._extract_city(t),
                "confidence": 0.95
            }

        # ======================
        # MAPS / ROUTE
        # ======================
        if any(x in t for x in [
            "route", "map", "где", "как доехать",
            "distance", "from", "to", "маршрут"
        ]):
            return {
                "tool": "maps",
                "args": self._extract_location(t),
                "confidence": 0.90
            }

        # ======================
        # SEARCH
        # ======================
        if any(x in t for x in [
            "search", "найди", "find",
            "что такое", "who is", "кто такой"
        ]):
            return {
                "tool": "search",
                "args": t,
                "confidence": 0.80
            }

        # ======================
        # DEFAULT LLM
        # ======================
        return {
            "tool": "llm",
            "args": text,
            "confidence": 0.50
        }

    # ======================
    # SAFE CITY EXTRACTION
    # ======================
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

    # ======================
    # LOCATION EXTRACTION
    # ======================
    def _extract_location(self, text: str) -> str:
        return text.strip()


# =========================
# COMPATIBILITY LAYER
# =========================
class Router:
    """
    Orchestrator expects this class.
    Wraps ToolRouter safely.
    """

    def __init__(self):
        self.tool_router = ToolRouter()

    def route(self, text: str) -> dict:
        try:
            tool_result = self.tool_router.route(text)

            return {
                "type": tool_result.get("tool", "llm"),
                "args": tool_result.get("args"),
                "confidence": tool_result.get("confidence", 0.5)
            }

        except Exception as e:
            logger.warning(f"[ROUTER FAIL SAFE] {e}")

            return {
                "type": "llm",
                "args": text,
                "confidence": 0.0
            }