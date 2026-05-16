from __future__ import annotations

import json
import logging

import httpx

from app.settings import settings
from i18n.t import t as _t, ow_lang as _ow_lang_fn

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"
_TIMEOUT  = 10.0


# ─── RUSSIAN CASE NORMALIZATION ───────────────────────────────────────────────
# Kept here because it's pure normalization logic, not i18n.

_RU_SUFFIX_MAP: tuple[tuple[str, str], ...] = (
    ("бурге", "бург"),   ("граде", "град"),   ("роде",  "род"),
    ("даре",  "дар"),    ("оде",   "од"),      ("льске", "льск"),
    ("нске",  "нск"),    ("вске",  "вск"),     ("йске",  "йск"),
    ("ске",   "ск"),     ("рге",   "рг"),      ("нге",   "нг"),
    ("ове",   "ов"),     ("же",    ""),         ("ни",    "нь"),
    ("ве",    "в"),      ("ге",    "г"),        ("ке",    "к"),
    ("ле",    "ль"),     ("ре",    "рь"),       ("пе",    "пь"),
    ("бе",    "бь"),     ("те",    "ть"),       ("де",    "дь"),
    ("зе",    "зь"),     ("се",    "сь"),       ("це",    "ць"),
    ("не",    "н"),      ("ие",    "ий"),
)

_RU_CITY_OVERRIDES: dict[str, str] = {
    "москве":            "Moscow",
    "санкт-петербурге":  "Saint Petersburg",
    "петербурге":        "Saint Petersburg",
    "питере":            "Saint Petersburg",
    "новосибирске":      "Novosibirsk",
    "екатеринбурге":     "Yekaterinburg",
    "казани":            "Kazan",
    "нижнем новгороде":  "Nizhny Novgorod",
    "челябинске":        "Chelyabinsk",
    "омске":             "Omsk",
    "самаре":            "Samara",
    "ростове-на-дону":   "Rostov-on-Don",
    "ростове":           "Rostov-on-Don",
    "уфе":               "Ufa",
    "красноярске":       "Krasnoyarsk",
    "перми":             "Perm",
    "воронеже":          "Voronezh",
    "волгограде":        "Volgograd",
    "краснодаре":        "Krasnodar",
    "саратове":          "Saratov",
    "тюмени":            "Tyumen",
    "тольятти":          "Tolyatti",
    "ижевске":           "Izhevsk",
    "барнауле":          "Barnaul",
    "ульяновске":        "Ulyanovsk",
    "владивостоке":      "Vladivostok",
    "хабаровске":        "Khabarovsk",
    "иркутске":          "Irkutsk",
    "ярославле":         "Yaroslavl",
    "махачкале":         "Makhachkala",
    "томске":            "Tomsk",
    "оренбурге":         "Orenburg",
    "кемерове":          "Kemerovo",
    "новокузнецке":      "Novokuznetsk",
    "рязани":            "Ryazan",
    "астрахани":         "Astrakhan",
    "набережных челнах": "Naberezhnye Chelny",
    "пензе":             "Penza",
    "липецке":           "Lipetsk",
    "кирове":            "Kirov",
    "чебоксарах":        "Cheboksary",
    "калининграде":      "Kaliningrad",
    "тбилиси":           "Tbilisi",
    "киеве":             "Kyiv",
    "харькове":          "Kharkiv",
    "одессе":            "Odessa",
    "минске":            "Minsk",
    "алматы":            "Almaty",
    "ташкенте":          "Tashkent",
    "баку":              "Baku",
    "ереване":           "Yerevan",
    "бишкеке":           "Bishkek",
    "душанбе":           "Dushanbe",
    "ашхабаде":          "Ashgabat",
}

_LOCATIVE_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ში",  ""),   ("ზე",  ""),   ("დან", ""),
    ("UM",  ""),   ("ից",  ""),
    ("'da",  ""),  ("'de",  ""),  ("'ta",  ""),  ("'te",  ""),
    ("da",   ""),  ("de",   ""),
)

_LOCATIVE_CITY_OVERRIDES: dict[str, str] = {
    "სიდნეიში":   "Sydney",    "სიდნეი":     "Sydney",
    "ლონდონში":   "London",    "ლონდონი":    "London",
    "პარიზში":    "Paris",     "პარიზი":     "Paris",
    "ნიუ-იორკში": "New York",  "ნიუ-იორკი":  "New York",
    "ბერლინში":   "Berlin",    "ბერლინი":    "Berlin",
    "ტოკიოში":    "Tokyo",     "ტოკიო":      "Tokyo",
    "დუბაიში":    "Dubai",     "დუბაი":      "Dubai",
    "სტამბოლში":  "Istanbul",  "სტამბოლი":   "Istanbul",
    "ბარსელონაში":"Barcelona", "ბარსელონა":  "Barcelona",
    "რომში":      "Rome",      "რომი":       "Rome",
    "ამსტერდამში":"Amsterdam", "ამსტერდამი": "Amsterdam",
    "მოსკოვში":   "Moscow",    "მოსკოვი":    "Moscow",
    "მადრიდში":   "Madrid",    "მადრიდი":    "Madrid",
    "Սиднейум":  "Sydney",    "Լонدонум":  "London",
    "Паризум":   "Paris",     "Берлинум":  "Berlin",
    "Токиойум":  "Tokyo",     "Дубайум":   "Dubai",
}


def _normalize_ru_city(city: str) -> str:
    lower = city.lower().strip()
    override = _RU_CITY_OVERRIDES.get(lower)
    if override:
        return override
    for suffix, replacement in _RU_SUFFIX_MAP:
        if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
            stem = city[: -len(suffix)]
            return stem + replacement
    return city


def _strip_locative(city: str) -> str:
    stripped = city.strip()
    override = (
        _LOCATIVE_CITY_OVERRIDES.get(stripped)
        or _LOCATIVE_CITY_OVERRIDES.get(stripped.lower())
    )
    if override:
        return override
    for suffix, replacement in _LOCATIVE_SUFFIXES:
        if stripped.endswith(suffix) and len(stripped) > len(suffix) + 2:
            return stripped[: -len(suffix)] + replacement
    return stripped


# ─── CITY EXTRACTOR ───────────────────────────────────────────────────────────

async def _extract_city(query: str) -> str:
    """
    Extract city name from a weather query in any language.
    ALWAYS returns city in Latin script (English) — OpenWeatherMap
    does not support non-Latin scripts (Georgian, Arabic, Chinese etc.)
    in the q= parameter. Without this, Georgian ვარშავა → 404.
    Delegates to Groq LLM; falls back to raw query.
    """
    try:
        from llm.groq_client import groq_client
        prompt = (
            "Extract the city name from the following weather query. "
            "Reply with a JSON object only, no extra text: "
            '{"city": "..."}. '
            "CRITICAL: always write the city name in English (Latin script), "
            "regardless of the language of the query. "
            "Examples: query 'ვარშავა' → {\"city\": \"Warsaw\"}, "
            "query 'Москва' → {\"city\": \"Moscow\"}, "
            "query 'طوكيو' → {\"city\": \"Tokyo\"}. "
            "If no city is mentioned, use an empty string.\n\n"
            f"Query: {query}"
        )
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.0,
        )
        raw = response.text
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        city = data.get("city", "").strip()
        if city:
            return _strip_locative(_normalize_ru_city(city))
    except Exception as exc:
        logger.warning("_extract_city LLM failed", extra={"error": str(exc)})

    # Fallback: if query is ASCII/Latin — try it directly with OWM (tolerant geocoder).
    # If non-Latin script (Georgian, Arabic, Chinese etc.) — return "" so the caller
    # gets an empty city and reports "city not found" rather than sending garbage to OWM
    # which would cause a 404.
    if all(ord(c) < 128 for c in query.strip()):
        return query.strip()
    return ""


# ─── ICON MAP ─────────────────────────────────────────────────────────────────

_WEATHER_ICON_MAP: dict[str, str] = {
    "01d": "☀️",  "01n": "🌙",
    "02d": "🌤️",  "02n": "🌤️",
    "03d": "⛅",   "03n": "⛅",
    "04d": "☁️",   "04n": "☁️",
    "09d": "🌧️",  "09n": "🌧️",
    "10d": "🌦️",  "10n": "🌦️",
    "11d": "⛈️",  "11n": "⛈️",
    "13d": "❄️",   "13n": "❄️",
    "50d": "🌫️",  "50n": "🌫️",
}


def _ow_lang(lang: str) -> str:
    return _ow_lang_fn(lang)


# ─── SERVICE ──────────────────────────────────────────────────────────────────

class WeatherService:
    """
    OpenWeatherMap API client.
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

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/weather",
                    params={
                        "q":     city,
                        "appid": self._api_key,
                        "units": units,
                        "lang":  _ow_lang(lang),
                    },
                )
                response.raise_for_status()
                logger.info("Weather fetched", extra={"city": city, "lang": lang})
                return response.json()
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

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/forecast",
                    params={
                        "q":     city,
                        "appid": self._api_key,
                        "units": units,
                        "lang":  _ow_lang(lang),
                        "cnt":   cnt,
                    },
                )
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
            emoji    = _WEATHER_ICON_MAP.get(icon, "🌤️")

            fl  = _t("weather_feels_like", lang) or "feels like"
            hum = _t("weather_humidity",   lang) or "Humidity"
            wnd = _t("weather_wind",       lang) or "Wind"

            return (
                f"{emoji} {location}\n"
                f"{desc}\n"
                f"🌡 {temp:.0f}°C ({fl} {feels:.0f}°C)\n"
                f"💧 {hum}: {humidity}%\n"
                f"💨 {wnd}: {wind} m/s"
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
                emoji  = _WEATHER_ICON_MAP.get(icon, "🌤️")
                lines.append(f"  {emoji} {dt_txt}: {temp:.0f}°C, {desc}")

            return "\n".join(lines)
        except Exception as exc:
            logger.error("format_forecast failed", extra={"error": str(exc)})
            return "⚠️ Could not format forecast data."


# Singleton
weather_service = WeatherService()