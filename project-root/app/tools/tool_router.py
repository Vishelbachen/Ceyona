import os
import requests


class ToolRouter:
    def __init__(self):
        self.mapbox_token = os.getenv("MAPBOX_TOKEN", "")
        self.weather_key = os.getenv("OPENWEATHER_API_KEY", "")

    async def route(self, intent: dict):
        if not intent:
            return None

        tool = intent.get("tool")
        query = intent.get("query")

        if tool == "map":
            return await self._map(query)

        if tool == "weather":
            return await self._weather(query)

        return None

    async def _map(self, query: str):
        if not self.mapbox_token or not query:
            return None

        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

            params = {
                "access_token": self.mapbox_token,
                "limit": 1
            }

            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            if not data.get("features"):
                return None

            feature = data["features"][0]

            return {
                "type": "map",
                "query": query,
                "place_name": feature.get("place_name"),
                "longitude": feature["center"][0],
                "latitude": feature["center"][1]
            }

        except:
            return None

    async def _weather(self, query: str):
        if not self.weather_key or not query:
            return None

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"

            params = {
                "q": query,
                "appid": self.weather_key,
                "units": "metric"
            }

            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            if r.status_code != 200:
                return None

            return {
                "type": "weather",
                "city": data.get("name"),
                "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"]
            }

        except:
            return None