from __future__ import annotations

import logging

import httpx

from app.settings import settings
from i18n.strings import t as _i18n, ow_lang as _ow_lang_fn

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_TIMEOUT = 10.0



def _ow_lang(lang: str) -> str:
    return _ow_lang_fn(lang)


def _label(key: str, lang: str) -> str:
    mapping = {
        "feels_like": "weather_feels_like",
        "humidity": "weather_humidity",
        "wind": "weather_wind",
    }
    i18n_key = mapping.get(key, key)
    return _i18n(i18n_key, lang) or key


def _weather_icon(icon_code: str) -> str:
    _MAP = {
        "01d": "☀️",  "01n": "🌙",
        "02d": "🌤️",  "02n": "🌤️",
        "03d": "⛅",  "03n": "⛅",
        "04d": "☁️",  "04n": "☁️",
        "09d": "🌧️",  "09n": "🌧️",
        "10d": "🌦️",  "10n": "🌦️",
        "11d": "⛈️",  "11n": "⛈️",
        "13d": "❄️",  "13n": "❄️",
        "50d": "🌫️",  "50n": "🌫️",
    }
    return _MAP.get(icon_code, "🌤️")


class WeatherService:
    """
    OpenWeather API client.
    Read-only. No state. No business logic.
    """

    def __init__(self) -> None:
        self._api_key = settings.openweather_api_key

    async def get_current(
        self,
        city: str,
        lang: str = "en",
        units: str = "metric",
    ) -> dict | None:
        if not self._api_key:
            logger.warning("OpenWeather API key not set")
            return None

        params = {
            "q": city,
            "appid": self._api_key,
            "units": units,
            "lang": _ow_lang(lang),
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{_BASE_URL}/weather", params=params)
                response.raise_for_status()
                data = response.json()
                logger.info("Weather fetched", extra={"city": city, "lang": lang})
                return data
        except Exception as exc:
            logger.error("WeatherService.get_current failed", extra={
                "city": city, "error": str(exc),
            })
            return None

    async def get_forecast(
        self,
        city: str,
        lang: str = "en",
        units: str = "metric",
        cnt: int = 5,
    ) -> dict | None:
        if not self._api_key:
            logger.warning("OpenWeather API key not set")
            return None

        params = {
            "q": city,
            "appid": self._api_key,
            "units": units,
            "lang": _ow_lang(lang),
            "cnt": cnt,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(f"{_BASE_URL}/forecast", params=params)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("WeatherService.get_forecast failed", extra={
                "city": city, "error": str(exc),
            })
            return None

    def format_current(self, data: dict, lang: str = "en") -> str:
        try:
            city     = data.get("name", "Unknown")
            country  = data.get("sys", {}).get("country", "")
            temp     = data["main"]["temp"]
            feels    = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            desc     = data["weather"][0]["description"].capitalize()
            wind     = data["wind"]["speed"]
            icon     = data["weather"][0].get("icon", "")

            location = f"{city}, {country}" if country else city
            emoji    = _weather_icon(icon)

            return (
                f"{emoji} {location}\n"
                f"{desc}\n"
                f"🌡 {temp:.0f}°C ({_label('feels_like', lang)} {feels:.0f}°C)\n"
                f"💧 {_label('humidity', lang)}: {humidity}%\n"
                f"💨 {_label('wind', lang)}: {wind} m/s"
            )
        except Exception as exc:
            logger.error("format_current failed", extra={"error": str(exc)})
            return "⚠️ Could not format weather data."

    def format_forecast(self, data: dict, lang: str = "en") -> str:
        try:
            city  = data.get("city", {}).get("name", "Unknown")
            items = data.get("list", [])

            if not items:
                return "⚠️ No forecast data available."

            lines = [f"📅 {city}:"]
            for item in items:
                dt_txt = item.get("dt_txt", "")
                temp   = item["main"]["temp"]
                desc   = item["weather"][0]["description"].capitalize()
                icon   = item["weather"][0].get("icon", "")
                emoji  = _weather_icon(icon)
                lines.append(f"  {emoji} {dt_txt}: {temp:.0f}°C, {desc}")

            return "\n".join(lines)
        except Exception as exc:
            logger.error("format_forecast failed", extra={"error": str(exc)})
            return "⚠️ Could not format forecast data."


# Singleton
weather_service = WeatherService()