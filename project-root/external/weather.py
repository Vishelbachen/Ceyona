import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_TIMEOUT = 10.0

# Supported languages for OpenWeather API
_OW_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh_cn", "ja": "ja", "ko": "ko",
    "pl": "pl", "uk": "uk", "fa": "fa",
}


def _ow_lang(lang: str) -> str:
    return _OW_LANG_MAP.get(lang, "en")


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
        """
        Fetch current weather for a city.
        Returns raw OpenWeather response dict or None on error.
        """
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
                "city": city,
                "error": str(exc),
            })
            return None

    async def get_forecast(
        self,
        city: str,
        lang: str = "en",
        units: str = "metric",
        cnt: int = 5,
    ) -> dict | None:
        """
        Fetch 5-day / 3-hour forecast for a city.
        cnt = number of 3-hour steps to return.
        """
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
                "city": city,
                "error": str(exc),
            })
            return None

    def format_current(self, data: dict, lang: str = "en") -> str:
        """
        Format raw weather data in