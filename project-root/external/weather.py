import logging
import httpx
from app.settings import settings

logger = logging.getLogger(__name__)
_BASE = "https://api.openweathermap.org/data/2.5"
_TIMEOUT = 10.0


async def get_weather(city: str, lang: str = "en") -> dict:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{_BASE}/weather", params={
                "q": city,
                "appid": settings.openweather_api_key,
                "units": "metric",
                "lang": lang,
            })
            r.raise_for_status()
            d = r.json()
            return {
                "city": d["name"],
                "temp": d["main"]["temp"],
                "feels_like": d["main"]["feels_like"],
                "description": d["weather"][0]["description"],
                "humidity": d["main"]["humidity"],
                "wind_speed": d["wind"]["speed"],
            }
    except Exception as exc:
        logger.error("Weather fetch failed", extra={"city": city, "error": str(exc)})
        return {}