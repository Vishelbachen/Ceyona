import os
import httpx


API_KEY = os.getenv("OPENWEATHER_API_KEY")


async def get_weather(city: str):
    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    data = response.json()

    if "main" not in data:
        return "Weather not found"

    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]

    return f"{city}: {temp}°C, {desc}"