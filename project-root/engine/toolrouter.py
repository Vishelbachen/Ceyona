import os
import requests


class ToolRouter:
    """
    Централизованный роутер инструментов (maps, weather, etc.)
    """

    def __init__(self):
        self.google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY")

    # =========================
    # MAIN ENTRY
    # =========================
    async def route(self, text: str) -> dict | None:
        """
        Returns:
        - dict (tool result)
        - None (if should go to LLM)
        """

        if not text:
            return None

        t = text.lower().strip()

        # =========================
        # MAP TOOL
        # =========================
        if t.startswith("map"):
            query = text[3:].strip()
            return await self.handle_map(query)

        # =========================
        # WEATHER TOOL
        # =========================
        if t.startswith("weather"):
            query = text[7:].strip()
            return await self.handle_weather(query)

        return None

    # =========================
    # GOOGLE MAPS (GEOCODING SIMPLE)
    # =========================
    async def handle_map(self, query: str) -> dict:
        if not self.google_maps_key:
            return {"error": "GOOGLE_MAPS_API_KEY missing"}

        if not query:
            return {"error": "empty map query"}

        url = "https://maps.googleapis.com/maps/api/geocode/json"

        params = {
            "address": query,
            "key": self.google_maps_key
        }

        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()

            if data.get("status") != "OK":
                return {
                    "error": data.get("error_message", data.get("status"))
                }

            result = data["results"][0]

            return {
                "type": "map",
                "query": query,
                "formatted_address": result["formatted_address"],
                "location": result["geometry"]["location"],
                "place_id": result["place_id"]
            }

        except Exception as e:
            return {"error": str(e)}

    # =========================
    # WEATHER (OpenWeather)
    # =========================
    async def handle_weather(self, query: str) -> dict:
        if not self.openweather_key:
            return {"error": "OPENWEATHER_API_KEY missing"}

        if not query:
            return {"error": "empty weather query"}

        url = "https://api.openweathermap.org/data/2.5/weather"

        params = {
            "q": query,
            "appid": self.openweather_key,
            "units": "metric"
        }

        try:
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