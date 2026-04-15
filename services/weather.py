import requests


class WeatherService:
    def __init__(self, settings):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, city: str, lang: str = "en") -> dict:
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": lang
        }

        response = requests.get(self.base_url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        return {
            "city": city,
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "condition": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind": data["wind"]["speed"]
        }