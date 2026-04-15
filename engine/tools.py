from services.weather import WeatherService
from services.maps import MapsService
from services.search import SearchService


class Tools:
    def __init__(self, settings, db=None):
        self.weather = WeatherService(settings)
        self.maps = MapsService(settings)
        self.search = SearchService(settings)

    async def execute(self, route: str, text: str) -> dict:
        """
        Simple intent-based tool router
        (no AI overhead, deterministic routing)
        """

        route = route.lower()

        # -------------------------
        # WEATHER INTENT
        # -------------------------
        if "weather" in route:
            city = self._extract_city(text)
            return self.weather.get_weather(city)

        # -------------------------
        # MAPS / GEO INTENT
        # -------------------------
        if "map" in route or "geo" in route:
            return self.maps.geocode(text)

        # -------------------------
        # SEARCH INTENT
        # -------------------------
        if "search" in route:
            return self.search.search(text)

        return {"status": "no_tool_used"}

    def _extract_city(self, text: str) -> str:
        """
        Minimal safe heuristic (no AI dependency)
        """
        return text.split()[-1]