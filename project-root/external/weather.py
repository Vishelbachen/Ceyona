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
    "pl": "pl", "uk": "uk", "fa": "fa", "nl": "nl",
    "sv": "sv", "no": "no", "da": "da", "fi": "fi",
    "cs": "cs", "sk": "sk", "ro": "ro", "hu": "hu",
    "bg": "bg", "hr": "hr", "sr": "sr", "he": "he",
    "vi": "vi", "th": "th", "id": "id", "ms": "ms",
    # unsupported by OpenWeather → neutral English fallback
    "hi": "en", "bn": "en", "ur": "en", "az": "en",
    "kk": "en", "uz": "en", "ka": "en", "hy": "en",
    "mn": "en", "si": "en", "km": "en", "lo": "en",
    "my": "en", "am": "en", "sw": "en",
}

_LABELS: dict[str, dict[str, str]] = {
    "feels_like": {
        "en": "feels like", "ru": "ощущается как", "de": "gefühlt",
        "fr": "ressenti", "es": "sensación", "pt": "sensação",
        "it": "percepito", "tr": "hissedilen", "ar": "يبدو كأنه",
        "zh": "体感", "ja": "体感", "ko": "체감",
        "pl": "odczuwalna", "uk": "відчувається як", "fa": "احساس می‌شود",
        "nl": "gevoelstemperatuur", "sv": "känns som", "no": "føles som",
        "da": "føles som", "fi": "tuntuu kuin", "he": "מורגש כ",
        "hi": "feels like", "id": "terasa", "az": "hiss olunur",
        "kk": "сезіледі", "uz": "seziladi", "ka": "feels like",
    },
    "humidity": {
        "en": "Humidity", "ru": "Влажность", "de": "Luftfeuchtigkeit",
        "fr": "Humidité", "es": "Humedad", "pt": "Umidade",
        "it": "Umidità", "tr": "Nem", "ar": "الرطوبة",
        "zh": "湿度", "ja": "湿度", "ko": "습도",
        "pl": "Wilgotność", "uk": "Вологість", "fa": "رطوبت",
        "nl": "Vochtigheid", "sv": "Luftfuktighet", "no": "Luftfuktighet",
        "da": "Luftfugtighed", "fi": "Kosteus", "he": "לחות",
        "hi": "Humidity", "id": "Kelembaban", "az": "Rütubət",
        "kk": "Ылғалдылық", "uz": "Namlik", "ka": "Humidity",
    },
    "wind": {
        "en": "Wind", "ru": "Ветер", "de": "Wind",
        "fr": "Vent", "es": "Viento", "pt": "Vento",
        "it": "Vento", "tr": "Rüzgar", "ar": "الرياح",
        "zh": "风速", "ja": "風速", "ko": "바람",
        "pl": "Wiatr", "uk": "Вітер", "fa": "باد",
        "nl": "Wind", "sv": "Vind", "no": "Vind",
        "da": "Vind", "fi": "Tuuli", "he": "רוח",
        "hi": "Wind", "id": "Angin", "az": "Külək",
        "kk": "Жел", "uz": "Shamol", "ka": "Wind",
    },
}


def _ow_lang(lang: str) -> str:
    return _OW_LANG_MAP.get(lang, "en")


def _label(key: str, lang: str) -> str:
    bucket = _LABELS.get(key, {})
    return bucket.get(lang) or bucket.get("en", key)


def _weather_icon(icon_code: str) -> str:
    _MAP = {
        "01d": "☀️",  "01n": "🌙",
        "02d": "🌤",  "02n": "🌤",
        "03d": "⛅️", "03n": "⛅️",
        "04d": "☁️",  "04n": "☁️",
        "09d": "🌧",  "09n": "🌧",
        "10d": "🌦",  "10n": "🌦",
        "11d": "⛈",  "11n": "⛈",
        "13d": "❄️",  "13n": "❄️",
        "50d": "🌫",  "50n": "🌫",
    }
    return _MAP.get(icon_code, "🌤")


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