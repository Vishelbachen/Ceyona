# engine/tool_router.py

import os
import requests


class ToolRouter:
    def __init__(self):
        self.google_maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY")

    async def route(self, text: str):
        if not text:
            return None

        t = text.lower().strip()

        if t.startswith("map"):
            return await self.handle_map(text[3:].strip())

        if t.startswith("weather"):
            return await self.handle_weather(text[7:].strip())

        return None

    async def handle_map(self, query: str):
        if not self.google_maps_key:
            return {"error": "GOOGLE_MAPS_API_KEY missing"}

        url = "https://maps.googleapis.com/maps/api/geocode/json"

        r = requests.get(url, params={
            "address": query,
            "key": self.google_maps_key
        })

        return r.json()

    async def handle_weather(self, query: str):
        if not self.openweather_key:
            return {"error": "OPENWEATHER_API_KEY missing"}

        url = "https://api.openweathermap.org/data/2.5/weather"

        r = requests.get(url, params={
            "q": query,
            "appid": self.openweather_key,
            "units": "metric"
        })

        return r.json()