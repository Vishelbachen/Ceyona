import logging
from typing import Dict, Any

from services.weather import WeatherService
from services.maps import MapsService
from services.search import SearchService

logger = logging.getLogger(__name__)


class Tools:
    """
    PRO TOOL EXECUTOR v3
    - structured execution
    - safe fallback
    - GPT-style output format
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
        if not route:
            return self._empty()

        tool = (route.get("tool") or "llm").lower()
        args = route.get("args")

        try:
            # =========================
            # WEATHER
            # =========================
            if tool == "weather":
                city = args if isinstance(args, str) else "Tbilisi"
                data = self.weather.get_weather(city)

                return self._wrap("weather", data)

            # =========================
            # MAPS
            # =========================
            if tool == "maps":
                data = self.maps.geocode(args or text)
                return self._wrap("maps", data)

            # =========================
            # SEARCH
            # =========================
            if tool == "search":
                data = self.search.search(args or text)
                return self._wrap("search", data)

            # =========================
            # LLM fallback
            # =========================
            if tool == "llm":
                return {
                    "tool": "llm",
                    "data": text,
                    "status": "passed_to_solver"
                }

            return self._empty()

        except Exception as e:
            logger.exception(f"[TOOLS ERROR]: {e}")
            return {
                "tool": "error",
                "message": str(e)
            }

    # =========================
    # RESPONSE WRAPPER (GPT STYLE)
    # =========================
    def _wrap(self, tool: str, data: Any) -> Dict[str, Any]:
        return {
            "tool": tool,
            "data": data,
            "status": "success"
        }

    # =========================
    # EMPTY SAFE RESPONSE
    # =========================
    def _empty(self) -> Dict[str, Any]:
        return {
            "tool": "none",
            "data": None,
            "status": "no_action"
        }