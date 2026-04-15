import logging
from typing import Dict, Any

from services.weather import WeatherService
from services.maps import MapsService
from services.search import SearchService

logger = logging.getLogger(__name__)


class Tools:
    """
    PRO TOOL EXECUTOR V2++
    - safe execution
    - structured output
    - crash-proof
    """

    def __init__(self, settings, db=None):
        self.weather = WeatherService(settings)
        self.maps = MapsService(settings)
        self.search = SearchService(settings)
        self.db = db

    async def execute(self, route: dict, text: str) -> Dict[str, Any]:
        try:
            if not route:
                return self._empty()

            tool = (route.get("type") or "llm").lower()
            args = route.get("args")

            # ======================
            # WEATHER
            # ======================
            if tool == "weather":
                city = self._safe_city(args, text)
                data = self.weather.get_weather(city)

                return self._wrap("weather", data)

            # ======================
            # MAPS
            # ======================
            if tool == "maps":
                data = self.maps.geocode(args or text)
                return self._wrap("maps", data)

            # ======================
            # SEARCH
            # ======================
            if tool == "search":
                data = self.search.search(args or text)
                return self._wrap("search", data)

            # ======================
            # LLM PASS THROUGH
            # ======================
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
                "message": str(e),
                "status": "failed"
            }

    def _safe_city(self, args, text: str) -> str:
        if isinstance(args, str) and args.strip():
            return args

        return text.split()[-1] if text else "Tbilisi"

    def _wrap(self, tool: str, data: Any) -> Dict[str, Any]:
        return {
            "tool": tool,
            "data": data,
            "status": "success"
        }

    def _empty(self) -> Dict[str, Any]:
        return {
            "tool": "none",
            "data": None,
            "status": "no_action"
        }