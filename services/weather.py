import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self, settings):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, city: str, lang: str = "en") -> Dict[str, Any]:
        if not city:
            return {"error": "empty_city"}

        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": lang
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "city": city,
                "temp": data.get("main", {}).get("temp"),
                "feels_like": data.get("main", {}).get("feels_like"),
                "condition": (data.get("weather") or [{}])[0].get("description"),
                "humidity": data.get("main", {}).get("humidity"),
                "wind": data.get("wind", {}).get("speed"),
            }

        except requests.RequestException as e:
            logger.warning(f"[WEATHER API FAIL] {e}")
            return {"error": "api_failed"}

        except Exception as e:
            logger.exception(f"[WEATHER UNKNOWN ERROR] {e}")
            return {"error": "unknown"}