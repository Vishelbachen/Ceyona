from __future__ import annotations

import aiohttp
from typing import Dict, Any, Optional

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# WEATHER CLIENT
# =========================
class WeatherClient:
    """
    ROLE:
    - fetch raw weather data from external API
    - normalize response format
    - provide deterministic output for upper layers

    STRICT RULES:
    - no caching logic
    - no decision making
    - no formatting for UI
    - no reasoning about weather
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY

    # =========================
    # CURRENT WEATHER
    # =========================
    async def get_current_weather(
        self,
        city: str,
        units: str = "metric",
    ) -> Dict[str, Any]:

        url = f"{self.BASE_URL}/weather"

        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()

        return self._normalize_current(data)

    # =========================
    # FORECAST
    # =========================
    async def get_forecast(
        self,
        city: str,
        units: str = "metric",
    ) -> Dict[str, Any]:

        url = f"{self.BASE_URL}/forecast"

        params = {
            "q": city,
            "appid": self.api_key,
            "units": units,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()

        return self._normalize_forecast(data)

    # =========================
    # NORMALIZATION (CURRENT)
    # =========================
    def _normalize_current(self, data: Dict[str, Any]) -> Dict[str, Any]:

        return {
            "city": data.get("name"),
            "temperature": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "humidity": data.get("main", {}).get("humidity"),
            "condition": data.get("weather", [{}])[0].get("main"),
            "description": data.get("weather", [{}])[0].get("description"),
            "wind_speed": data.get("wind", {}).get("speed"),
            "raw": data,
        }

    # =========================
    # NORMALIZATION (FORECAST)
    # =========================
    def _normalize_forecast(self, data: Dict[str, Any]) -> Dict[str, Any]:

        return {
            "city": data.get("city", {}).get("name"),
            "list": [
                {
                    "time": item.get("dt_txt"),
                    "temp": item.get("main", {}).get("temp"),
                    "condition": item.get("weather", [{}])[0].get("main"),
                    "description": item.get("weather", [{}])[0].get("description"),
                }
                for item in data.get("list", [])
            ],
            "raw": data,
        }