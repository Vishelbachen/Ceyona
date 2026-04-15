import re
import logging

logger = logging.getLogger(__name__)


# =========================
# TOOL ROUTER (CORE ENGINE)
# =========================
class ToolRouter:
    """
    PRO TOOL ROUTER v4 (production hardened)
    - deterministic
    - crash-safe
    - improved NLP heuristics
    - zero-dependency intelligence layer
    """

    def route(self, text: str) -> dict:
        try:
            t = (text or "").lower().strip()

            if not t:
                return self._llm_fallback(text)

            # ======================
            # WEATHER INTENT
            # ======================
            if self._match(t, ["weather", "погода", "температура", "forecast"]):
                return {
                    "tool": "weather",
                    "args": self._extract_city(t),
                    "confidence": 0.97
                }

            # ======================
            # MAPS / ROUTE INTENT
            # ======================
            if self._match(t, [
                "route", "map", "maps", "где", "как доехать",
                "distance", "from", "to", "маршрут", "дорога", "ехать"
            ]):
                return {
                    "tool": "maps",
                    "args": self._extract_location(t),
                    "confidence": 0.93
                }

            # ======================
            # SEARCH INTENT
            # ======================
            if self._match(t, [
                "search", "найди", "find",
                "что такое", "who is", "кто такой", "explain"
            ]):
                return {
                    "tool": "search",
                    "args": t,
                    "confidence": 0.85
                }

            # ======================
            # DEFAULT
            # ======================
            return {
                "tool": "llm",
                "args": text,
                "confidence": 0.55
            }

        except Exception as e:
            logger.warning(f"[TOOL ROUTER ERROR] {e}")
            return self._llm_fallback(text)

    # ======================
    # FAST MATCH ENGINE
    # ======================
    def _match(self, text: str, keywords: list) -> bool:
        return any(k in text for k in keywords)

    # ======================
    # CITY EXTRACTION (ROBUST)
    # ======================
    def _extract_city(self, text: str) -> str:
        try:
            if not text:
                return "Tbilisi"

            # remove noise words
            blacklist = {
                "weather", "погода", "today", "now",
                "сегодня", "какая", "температура",
                "like", "is", "in", "at", "what"
            }

            words = re.split(r"\s+", text)

            candidates = []
            for w in words:
                clean = w.strip(",.?!:;")

                if (
                    clean and
                    clean not in blacklist and
                    len(clean) > 2 and
                    not clean.isdigit()
                ):
                    candidates.append(clean)

            # heuristic: last meaningful token = most likely city
            if candidates:
                return candidates[-1].capitalize()

            return "Tbilisi"

        except Exception:
            return "Tbilisi"

    # ======================
    # LOCATION EXTRACTION (SAFE)
    # ======================
    def _extract_location(self, text: str) -> str:
        try:
            return (text or "").strip()
        except Exception:
            return ""

    # ======================
    # FALLBACK
    # ======================
    def _llm_fallback(self, text: str) -> dict:
        return {
            "tool": "llm",
            "args": text or "",
            "confidence": 0.0
        }


# =========================
# COMPATIBILITY LAYER
# =========================
class Router:
    """
    Orchestrator compatibility layer
    - guarantees stable output schema
    - prevents crashes from ToolRouter
    """

    def __init__(self):
        self.tool_router = ToolRouter()

    def route(self, text: str) -> dict:
        try:
            result = self.tool_router.route(text)

            if not isinstance(result, dict):
                return self._safe_llm(text)

            return {
                "type": result.get("tool", "llm"),
                "args": result.get("args"),
                "confidence": float(result.get("confidence") or 0.5)
            }

        except Exception as e:
            logger.warning(f"[ROUTER FAIL SAFE] {e}")
            return self._safe_llm(text)

    def _safe_llm(self, text: str) -> dict:
        return {
            "type": "llm",
            "args": text or "",
            "confidence": 0.0
        }