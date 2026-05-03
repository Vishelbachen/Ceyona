from __future__ import annotations

import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_TIMEOUT = 10.0

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
                "city": city, "error": str(exc),
            })
            return None

    def format_current(self, data: dict, lang: str = "en") -> str:
    """
    Format raw OpenWeather current weather into a readable string.
    Localised output based on lang.
    """
    _LABELS: dict[str, dict[str, str]] = {
        "feels_like": {
            "en": "feels like", "ru": "ощущается как", "de": "gefühlt",
            "fr": "ressenti", "es": "sensación", "pt": "sensação",
            "it": "percepito", "tr": "hissedilen", "ar": "يبدو كأنه",
            "zh": "体感", "ja": "体感", "ko": "체감",
            "pl": "odczuwalna", "uk": "відчувається як", "fa": "احساس می‌شود",
            "nl": "gevoelstemperatuur", "sv": "känns som", "no": "føles som",
            "da": "føles som", "fi": "tuntuu kuin", "he": "מורגש כ",
            "hi": "महसूस होता है", "id": "terasa", "az": "hiss olunur",
            "kk": "сезіледі", "uz": "seziladi",
        },
        "humidity": {
            "en": "Humidity", "ru": "Влажность", "de": "Luftfeuchtigkeit",
            "fr": "Humidité", "es": "Humedad", "pt": "Umidade",
            "it": "Umidità", "tr": "Nem", "ar": "الرطوبة",
            "zh": "湿度", "ja": "湿度", "ko": "습도",
            "pl": "Wilgotność", "uk": "Вологість", "fa": "رطوبت",
            "nl": "Vochtigheid", "sv": "Luftfuktighet", "no": "Luftfuktighet",
            "da": "Luftfugtighed", "fi": "Kosteus", "he": "לחות",
            "hi": "आर्द्रता", "id": "Kelembaban", "az": "Rütubət",
            "kk": "Ылғалдылық", "uz": "Namlik",
        },
        "wind": {
            "en": "Wind", "ru": "Ветер", "de": "Wind",
            "fr": "Vent", "es": "Viento", "pt": "Vento",
            "it": "Vento", "tr": "Rüzgar", "ar": "الرياح",
            "zh": "风速", "ja": "風速", "ko": "바람",
            "pl": "Wiatr", "uk": "Вітер", "fa": "باد",
            "nl": "Wind", "sv": "Vind", "no": "Vind",
            "da": "Vind", "fi": "Tuuli", "he": "רוח",
            "hi": "हवा", "id": "Angin", "az": "Külək",
            "kk": "Жел", "uz": "Shamol",
        },
        "ms": {
            "en": "m/s", "ru": "м/с", "de": "m/s",
            "fr": "m/s", "es": "m/s", "pt": "m/s",
            "it": "m/s", "tr": "m/s", "ar": "م/ث",
            "zh": "米/秒", "ja": "m/s", "ko": "m/s",
            "pl": "m/s", "uk": "м/с", "fa": "م/ث",
            "nl": "m/s", "sv": "m/s", "no": "m/s",
            "da": "m/s", "fi": "m/s", "he": "מ/ש",
            "hi": "मी/से", "id": "m/s", "az": "m/s",
            "kk": "м/с", "uz": "m/s",
        },
    }

    def _l(key: str) -> str:
        return _LABELS[key].get(lang) or _LABELS[key]["en"]

    try:
        city     = data.get("name", "Unknown")
        country  = data.get("sys", {}).get("country", "")
        temp     = data["main"]["temp"]
        feels    = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc     = data["weather"][0]["description"].capitalize()
        wind     = data["wind"]["speed"]

        location = f"{city}, {country}" if country else city

        return (
            f"🌤 {location}\n"
            f"{desc}\n"
            f"🌡 {temp:.0f}°C ({_l('feels_like')} {feels:.0f}°C)\n"
            f"💧 {_l('humidity')}: {humidity}%\n"
            f"💨 {_l('wind')}: {wind} m/s {_l('ms')}"
        )
    except Exception as exc:
        logger.error("format_current failed", extra={"error": str(exc)})
        return "⚠️ Could not format weather data."