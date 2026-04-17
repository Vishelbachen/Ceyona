import os
import requests


class ToolRouter:
    """
    Mapbox-based tools (no Google dependency)
    """

    def __init__(self):
        self.mapbox_token = os.getenv("MAPBOX_TOKEN")
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY")

    # =========================
    # ENTRY POINT
    # =========================
    async def route(self, text: str):
        if not text:
            return None

        t = text.lower().strip()

        # MAP TOOL
        if t.startswith("map"):
            query = text[3:].strip()
            return await self.handle_map(query)

        # WEATHER TOOL
        if t.startswith("weather"):
            query = text[7:].strip()
            return await self.handle_weather(query)

        return None

    # =========================
    # MAPBOX GEOCODING
    # =========================
    async def handle_map(self, query: str):
        if not self.mapbox_token:
            return {"error": "MAPBOX_TOKEN missing"}

        if not query:
            return {"error": "empty query"}

        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

            params = {
                "access_token": self.mapbox_token,
                "limit": 1
            }

            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            if not data.get("features"):
                return {"error": "no results found"}

            feature = data["features"][0]

            return {
                "type": "map",
                "query": query,
                "place_name": feature.get("place_name"),
                "longitude": feature["center"][0],
                "latitude": feature["center"][1]
            }

        except Exception as e:
            return {"error": str(e)}

    # =========================
    # WEATHER (OpenWeather)
    # =========================
    async def handle_weather(self, query: str):
        if not self.openweather_key:
            return {"error": "OPENWEATHER_API_KEY missing"}

        try:
            url = "https://api.openweathermap.org/data/2.5/weather"

            params = {
                "q": query,
                "appid": self.openweather_key,
                "units": "metric"
            }

            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            if r.status_code != 200:
                return {"error": data.get("message", "weather error")}

            return {
                "type": "weather",
                "city": data["name"],
                "temp": data["main"]["temp"],
                "description": data["weather"][0]["description"]
            }

        except Exception as e:
            return {"error": str(e)}