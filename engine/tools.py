import logging
from typing import Dict, Any

from services.weather import WeatherService
from services.maps import MapsService
from services.search import SearchService

logger = logging.getLogger(__name__)


class Tools:
    """
    Tool Execution Layer v2 (Ceyona AI)
    - deterministic routing
    - safe fallback
    - structured outputs
    """

    def __init__(self, settings, db=None):
        self.weather = WeatherService(settings)
        self.maps = MapsService(settings)
        self.search = SearchService(settings)
        self.db = db

    # =========================
    # MAIN EXECUTOR
    # =========================
    async def execute(self, route: dict, text: str) -> Dict[str, Any]:
        """
        route example:
        {
            "type": "weather",
            "domain": "api"
        }
        """

        if not route:
            return {"status": "no_route"}

        tool = (route.get("type") or "").lower()

        try:
            # =========================
            # WEATHER TOOL
            # =========================
            if tool == "weather":
                city = self._extract_city(text)
                data = self.weather.get_weather(city)

                return {
                    "tool": "weather",
                    "data": data
                }

            # =========================
            # MAPS TOOL
            # =========================
            if tool == "maps":
                data = self.maps.geocode(text)

                return {
                    "tool": "maps",
                    "data": data
                }

            # =========================
            # SEARCH TOOL
            # =========================
            if tool == "search":
                data = self.search.search(text)

                return {
                    "tool": "search",
                    "data": data
                }

            # =========================
            # NO TOOL
            # =========================
            return {
                "tool": "none",
                "data": None
            }

        except Exception as e:
            logger.exception(f"[TOOLS ERROR]: {e}")
            return {
                "tool": "error",
                "message": str(e)
            }

    # =========================
    # CITY EXTRACTION (SAFE v2)
    # =========================
    def _extract_city(self, text: str) -> str:
        """
        Better heuristic without ML dependency
        """

        if not text:
            return "Tbilisi"

        blacklist = {
            "weather", "погода", "today", "сегодня",
            "какая", "каков", "температура", "now"
        }

        words = text.replace(",", " ").split()

        candidates = [
            w for w in words
            if w.lower() not in blacklist and len(w) > 2
        ]

        if not candidates:
            return "Tbilisi"

        # last meaningful token = most likely city
        return candidates[-1]