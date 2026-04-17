import os
import requests
import re
import asyncio


class ToolRouter:
    """
    Production Tool Router v2
    - regex intent detection
    - no LLM bypass
    - async-safe requests
    """

    def __init__(self):
        self.google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY")

    # =========================
    # MAIN ENTRY
    # =========================
    async def route(self, text: str):
        if not text:
            return None

        t = text.lower().strip()

        # =========================
        # MAP INTENT DETECTION (ROBUST)
        # =========================
        if re.search(r"^(map|maps|show map|open map)\b", t):
            query = self._extract_after_keyword(text)
            return await self.handle_map(query)

        # =========================
        # WEATHER INTENT DETECTION
        # =========================
        if re.search(r"^(weather|forecast)\b", t):
            query = self._extract_after_keyword(text)
            return await self.handle_weather(query)

        return None

    # =========================
    # EXTRACT QUERY SAFELY
    # =========================
    def _extract_after_keyword(self, text: str) -> str:
        parts = text.split(" ", 1)
        if len(parts) == 1:
            return ""
        return parts[1].strip()

    # =========================
    # GOOGLE MAPS (GEOCODING)
    # =========================
    async def handle_map(self, query: str):
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
            data = await asyncio.to_thread(
                lambda: requests.get(url, params=params, timeout=10).json()
            )

            if data.get("status") != "OK":
                return {
                    "error": data.get("error_message", data.get("status"))
                }

            result = data["results"][0]

            return {
                "type": "map",
                "query": query,
                "formatted_address": result.get("formatted_address"),
                "location": result.get("geometry", {}).get("location"),
                "place_id": result.get("place_id")
            }

        except Exception as e:
            return {"error": str(e)}

    # =========================
    # WEATHER
    # =========================
    async def handle_weather(self, query: str):
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
            data = await asyncio.to_thread(
                lambda: requests.get(url, params=params, timeout=10).json()
            )

            if not data or data.get("cod") != 200:
                return {"error": data.get("message", "weather error")}

            return {
                "type": "weather",
                "city": data.get("name"),
                "temp": data.get("main", {}).get("temp"),
                "description": data.get("weather", [{}])[0].get("description")
            }

        except Exception as e:
            return {"error": str(e)}