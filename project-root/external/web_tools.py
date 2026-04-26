from __future__ import annotations

from typing import Dict, Any, Optional

from external.weather import WeatherClient
from external.maps import MapsClient
from external.search import SearchClient


# =========================
# WEB TOOLS AGGREGATOR
# =========================
class WebTools:
    """
    ROLE:
    - unified access point for external APIs
    - thin wrapper over specialized clients
    - normalize tool calling interface for upper layers

    STRICT RULES:
    - no reasoning
    - no ranking
    - no orchestration logic
    - no caching decisions
    """

    def __init__(
        self,
        weather: WeatherClient,
        maps: MapsClient,
        search: SearchClient,
    ):
        self.weather = weather
        self.maps = maps
        self.search = search

    # =========================
    # WEATHER
    # =========================
    async def weather_current(self, city: str) -> Dict[str, Any]:
        return await self.weather.get_current_weather(city)

    async def weather_forecast(self, city: str) -> Dict[str, Any]:
        return await self.weather.get_forecast(city)

    # =========================
    # MAPS
    # =========================
    async def geocode(self, query: str) -> Dict[str, Any]:
        return await self.maps.geocode(query)

    async def reverse_geocode(
        self,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        return await self.maps.reverse_geocode(lat, lon)

    # =========================
    # SEARCH
    # =========================
    async def web_search(
        self,
        query: str,
        limit: int = 5,
    ) -> Dict[str, Any]:
        return await self.search.search(query, limit=limit)