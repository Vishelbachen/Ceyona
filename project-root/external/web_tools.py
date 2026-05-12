from __future__ import annotations

import logging
import re

import httpx

from app.settings import settings
from i18n.t import t as _t, ow_lang as _ow_lang_fn

logger = logging.getLogger(__name__)

_TIMEOUT  = 15.0
_MAX_CHARS = 5000

# ─── RUSSIAN CASE NORMALIZATION ───────────────────────────────────────────────

_RU_SUFFIX_MAP: tuple[tuple[str, str], ...] = (
    ("бурге", "бург"),
    ("граде", "град"),
    ("роде",  "род"),
    ("даре",  "дар"),
    ("оде",   "од"),
    ("льске", "льск"),
    ("нске",  "нск"),
    ("вске",  "вск"),
    ("йске",  "йск"),
    ("ске",   "ск"),
    ("рге",   "рг"),
    ("нге",   "нг"),
    ("ове",   "ов"),
    ("же",    ""),
    ("ни",    "нь"),
    ("ве",    "в"),
    ("ге",    "г"),
    ("ке",    "к"),
    ("ле",    "ль"),
    ("ре",    "рь"),
    ("пе",    "пь"),
    ("бе",    "бь"),
    ("те",    "ть"),
    ("де",    "дь"),
    ("зе",    "зь"),
    ("се",    "сь"),
    ("це",    "ць"),
    ("не",    "н"),
    ("ие",    "ий"),
)

_RU_CITY_OVERRIDES: dict[str, str] = {
    "москве":               "Moscow",
    "санкт-петербурге":     "Saint Petersburg",
    "петербурге":           "Saint Petersburg",
    "питере":               "Saint Petersburg",
    "новосибирске":         "Novosibirsk",
    "екатеринбурге":        "Yekaterinburg",
    "казани":               "Kazan",
    "нижнем новгороде":     "Nizhny Novgorod",
    "челябинске":           "Chelyabinsk",
    "омске":                "Omsk",
    "самаре":               "Samara",
    "ростове-на-дону":      "Rostov-on-Don",
    "ростове":              "Rostov-on-Don",
    "уфе":                  "Ufa",
    "красноярске":          "Krasnoyarsk",
    "перми":                "Perm",
    "воронеже":             "Voronezh",
    "волгограде":           "Volgograd",
    "краснодаре":           "Krasnodar",
    "саратове":             "Saratov",
    "тюмени":               "Tyumen",
    "тольятти":             "Tolyatti",
    "ижевске":              "Izhevsk",
    "барнауле":             "Barnaul",
    "ульяновске":           "Ulyanovsk",
    "владивостоке":         "Vladivostok",
    "хабаровске":           "Khabarovsk",
    "иркутске":             "Irkutsk",
    "ярославле":            "Yaroslavl",
    "махачкале":            "Makhachkala",
    "томске":               "Tomsk",
    "оренбурге":            "Orenburg",
    "кемерове":             "Kemerovo",
    "новокузнецке":         "Novokuznetsk",
    "рязани":               "Ryazan",
    "астрахани":            "Astrakhan",
    "набережных челнах":    "Naberezhnye Chelny",
    "пензе":                "Penza",
    "липецке":              "Lipetsk",
    "кирове":               "Kirov",
    "чебоксарах":           "Cheboksary",
    "калининграде":         "Kaliningrad",
    "тбилиси":              "Tbilisi",
    "киеве":                "Kyiv",
    "харькове":             "Kharkiv",
    "одессе":               "Odessa",
    "минске":               "Minsk",
    "алматы":               "Almaty",
    "ташкенте":             "Tashkent",
    "баку":                 "Baku",
    "ереване":              "Yerevan",
    "бишкеке":              "Bishkek",
    "душанбе":              "Dushanbe",
    "ашхабаде":             "Ashgabat",
}

_CITY_STOP_WORDS: frozenset[str] = frozenset({
    # Russian
    "сейчас", "сегодня", "прямо", "там", "здесь", "это", "какая", "какой",
    "будет", "есть", "данный", "этот", "реальная", "реальный", "актуальная",
    # English
    "now", "today", "currently", "right", "there", "here", "the", "a", "an",
    "real", "current", "actual", "latest", "like", "what", "is", "weather",
    # Georgian
    "ამ", "ახლა", "წუთას", "დღეს", "რა", "არის",
    # Turkish
    "şu", "an", "şimdi", "bugün", "hava",
    # Arabic
    "الآن", "اليوم", "هناك", "في",
    # Hindi
    "अभी", "आज", "वहाँ",
    # Hausa
    "yaya", "yake", "yanzu",
    # Indonesian / Malay
    "sekarang", "hari", "ini",
    # Vietnamese
    "bây", "giờ", "hôm", "nay",
    # Swahili
    "sasa", "leo", "hali",
})

_WEATHER_PREPS = (
    # Russian
    "погода в ", "температура в ", "прогноз для ", "погоду в ",
    "погода для города ", "для города ",
    # English
    "weather in ", "temperature in ", "forecast for ", "in ",
    # German / French / Spanish / Portuguese
    "für ", "dans ", "en ", "para ",
    # Hausa: "yanayi yake a <City>" / "yanayi a <City>"
    "yanayi yake a ", "yanayi a ",
    # Turkish
    "de hava ", "hava durumu ", "hava ",
    # Arabic
    "الطقس في ", "في ",
    # Indonesian / Malay
    "cuaca di ", "di ",
    # Vietnamese
    "thời tiết ở ", "ở ",
    # Swahili
    "hali ya hewa ya ", "hali ya hewa ",
    # Hindi
    "का मौसम ", "में मौसम ",
    # Korean — keep short to avoid false matches
    "날씨 ",
)

_WEATHER_ICON_MAP: dict[str, str] = {
    "01d": "☀️",  "01n": "🌙",  "02d": "🌤️", "02n": "🌤️",
    "03d": "⛅",  "03n": "⛅",  "04d": "☁️",  "04n": "☁️",
    "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌦️",
    "11d": "⛈",  "11n": "⛈",  "13d": "❄️",  "13n": "❄️",
    "50d": "🌫️", "50n": "🌫️",
}





# Locative/case suffixes for non-Slavic languages that OWM doesn't understand.
# Georgian: -ში (-shi) = 'in'; Armenian: -ում (-um) = 'in'; etc.
_LOCATIVE_SUFFIXES: tuple[tuple[str, str], ...] = (
    # Georgian locatives
    ("ში",  ""),   # სიდნეიში → სიდნეი (Sydney)
    ("ზე",  ""),   # თბილისზე → თბილისი
    ("დან", ""),   # ლონდონიდან → ლონდონი
    ("ში",  ""),
    # Armenian locatives
    ("ում",  ""),  # Երևանում → Երևան
    ("ից",  ""),   # Երևանից → Երևան
    # Turkish locatives (supplement)
    ("'da",  ""),  # Istanbul'da → Istanbul
    ("'de",  ""),
    ("'ta",  ""),
    ("'te",  ""),
    ("da",   ""),   # Londonda → London (careful: only for known cities)
    ("de",   ""),
)

# Known city name mappings for locative forms (highest priority)
_LOCATIVE_CITY_OVERRIDES: dict[str, str] = {
    # Georgian
    "სიდნეიში":    "Sydney",
    "სიდნეი":      "Sydney",
    "ლონდონში":    "London",
    "ლონდონი":     "London",
    "პარიზში":     "Paris",
    "პარიზი":      "Paris",
    "ნიუ-იორკში":  "New York",
    "ნიუ-იორკი":   "New York",
    "ბერლინში":    "Berlin",
    "ბერლინი":     "Berlin",
    "ტოკიოში":     "Tokyo",
    "ტოკიო":       "Tokyo",
    "დუბაიში":     "Dubai",
    "დუბაი":       "Dubai",
    "სტამბოლში":   "Istanbul",
    "სტამბოლი":    "Istanbul",
    "ბარსელონაში": "Barcelona",
    "ბარსელონა":   "Barcelona",
    "რომში":       "Rome",
    "რომი":        "Rome",
    "ამსტერდამში": "Amsterdam",
    "ამსტერდამი":  "Amsterdam",
    "მოსკოვში":    "Moscow",
    "მოსკოვი":     "Moscow",
    "მადრიდში":    "Madrid",
    "მადრიდი":     "Madrid",
    # Armenian
    "Սիդնեյում":   "Sydney",
    "Լոնդոնում":   "London",
    "Փարիզում":    "Paris",
    "Բեռլինում":   "Berlin",
    "Տոկիոյում":   "Tokyo",
    "Դուբայում":   "Dubai",
    # Hausa — 'a' + city (preposition, not suffix)
    # handled in _extract_city_hausa below
}


def _strip_locative(city: str) -> str:
    """Strip locative/case suffixes from city names in non-Slavic languages."""
    stripped = city.strip()
    # Check exact override first
    override = _LOCATIVE_CITY_OVERRIDES.get(stripped) or _LOCATIVE_CITY_OVERRIDES.get(stripped.lower())
    if override:
        return override
    # Try stripping known locative suffixes
    for suffix, replacement in _LOCATIVE_SUFFIXES:
        if stripped.endswith(suffix) and len(stripped) > len(suffix) + 2:
            return stripped[: -len(suffix)] + replacement
    return stripped


def _extract_city_hausa(query: str) -> str | None:
    """Extract city from Hausa weather queries. Pattern: 'a <City>'."""
    import re
    # 'yaya yanayi yake a San Francisco yanzu?' → 'San Francisco'
    m = re.search(r'\ba\s+([A-Z][\w\s]+?)(?:\s+yanzu|\s*\?|$)', query)
    if m:
        return m.group(1).strip()
    return None


def _normalize_ru_city(city: str) -> str:
    lower = city.lower().strip()
    if lower in _RU_CITY_OVERRIDES:
        return _RU_CITY_OVERRIDES[lower]
    for suffix, replacement in sorted(_RU_SUFFIX_MAP, key=lambda x: -len(x[0])):
        if lower.endswith(suffix) and len(lower) > len(suffix) + 2:
            base = lower[: -len(suffix)] + replacement
            return base.capitalize()
    return city.strip()


def _extract_city(query: str) -> str:
    lower = query.lower()

    if "ში" in query:
        for word in query.split():
            if word.endswith("ში") and len(word) > 4:
                city = word[:-2].rstrip("?.!,")
                if city.lower() not in _CITY_STOP_WORDS and len(city) > 2:
                    return city

    for prep in _WEATHER_PREPS:
        idx = lower.find(prep)
        if idx != -1:
            rest = query[idx + len(prep):].strip()
            city = re.split(r"[?,\n]", rest)[0].strip()
            words = city.split()
            while words and words[-1].lower() in _CITY_STOP_WORDS:
                words.pop()
            city = " ".join(words).rstrip("?.!,")
            if city and city.lower() not in _CITY_STOP_WORDS and len(city) > 1:
                return _strip_locative(_normalize_ru_city(city))

    # Hausa: 'a <City>' pattern
    hausa_city = _extract_city_hausa(query)
    if hausa_city:
        return hausa_city

    words = query.strip().rstrip("?.!,").split()
    candidates = [w for w in words if w.lower() not in _CITY_STOP_WORDS and len(w) > 2]
    if candidates:
        city = _normalize_ru_city(candidates[-1])
        # Apply locative stripping for non-Slavic scripts
        return _strip_locative(city)

    return query.strip()


def _extract_location(query: str) -> str:
    lower = query.lower()
    for kw in (
        "где находится", "где находятся", "местоположение", "адрес",
        "покажи на карте", "координаты", "покажи местоположение",
        "where is", "location of", "address of", "where are",
        "show on map", "coordinates of",
        "wo ist", "où est", "dónde está",
    ):
        idx = lower.find(kw)
        if idx != -1:
            loc = query[idx + len(kw):].strip()
            loc = re.split(r"[?,\n]", loc)[0].strip()
            if loc:
                return loc
    return query.strip()


def _format_weather(d: dict, lang: str) -> str:
    city    = d.get("name", "")
    country = d.get("sys", {}).get("country", "")
    temp    = d["main"]["temp"]
    feels   = d["main"]["feels_like"]
    humid   = d["main"]["humidity"]
    desc    = d["weather"][0]["description"].capitalize()
    wind    = d["wind"]["speed"]
    icon    = d["weather"][0].get("icon", "")
    emoji   = _WEATHER_ICON_MAP.get(icon, "🌤️")
    loc     = f"{city}, {country}" if country else city

    fl  = _t("weather_feels_like", lang) or "feels like"
    hum = _t("weather_humidity", lang)   or "Humidity"
    wnd = _t("weather_wind", lang)       or "Wind"

    return (
        f"{emoji} {loc}\n"
        f"{desc}\n"
        f"🌡 {temp:.0f}°C ({fl} {feels:.0f}°C)\n"
        f"💧 {hum}: {humid}%\n"
        f"💨 {wnd}: {wind} m/s"
    )


# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────

async def _weather(query: str, lang: str = "en") -> str:
    if not settings.openweather_api_key:
        return ""

    city = _extract_city(query)
    if not city:
        return ""

    ow_lang = _ow_lang_fn(lang)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q":     city,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                    "lang":  ow_lang,
                },
            )
            r.raise_for_status()
            return _format_weather(r.json(), lang)
    except Exception as exc:
        logger.error("Weather API failed", extra={"city": city, "error": str(exc)})
        return ""


async def _search(query: str, lang: str = "en") -> str:
    if not settings.serpapi_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={
                    "q":       query,
                    "api_key": settings.serpapi_key,
                    "num":     5,
                    "engine":  "google",
                    "hl":      lang,
                },
            )
            r.raise_for_status()
            data = r.json()

            results = []

            ab = data.get("answer_box", {})
            if ab.get("answer"):
                results.append(f"Direct answer: {ab['answer']}")
            elif ab.get("snippet"):
                results.append(f"Direct answer: {ab['snippet']}")

            kg = data.get("knowledge_graph", {})
            if kg.get("description"):
                results.append(f"Summary: {kg['description']}")

            for item in data.get("organic_results", [])[:5]:
                title   = item.get("title", "")
                snippet = item.get("snippet", "")
                link    = item.get("link", "")
                if snippet:
                    results.append(f"{title}: {snippet}\nSource: {link}")

            return "\n\n".join(results)[:_MAX_CHARS]

    except Exception as exc:
        logger.error("Search API failed", extra={"query": query[:50], "error": str(exc)})
        return ""


async def _maps(query: str, lang: str = "en") -> str:
    if not settings.mapbox_token:
        return ""

    location = _extract_location(query)
    if not location:
        location = query

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"https://api.mapbox.com/geocoding/v5/mapbox.places/{location}.json",
                params={
                    "access_token": settings.mapbox_token,
                    "limit":        1,
                    "language":     lang,
                },
            )
            r.raise_for_status()
            features = r.json().get("features", [])
            if not features:
                return ""

            f    = features[0]
            name = f.get("place_name", location)
            lon  = f["geometry"]["coordinates"][0]
            lat  = f["geometry"]["coordinates"][1]

            return (
                f"📍 {name}\n"
                f"Координаты: {lat:.5f}, {lon:.5f}\n"
                f"Google Maps: https://maps.google.com/?q={lat},{lon}"
            )
    except Exception as exc:
        logger.error("Maps API failed", extra={"query": query[:50], "error": str(exc)})
        return ""


async def _maps_poi(query: str, lang: str = "en") -> str:
    if not settings.serpapi_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine":  "google_maps",
                    "q":       query,
                    "api_key": settings.serpapi_key,
                    "hl":      lang,
                },
            )
            r.raise_for_status()
            data = r.json()

            results = []
            for place in data.get("local_results", [])[:3]:
                name    = place.get("title", "")
                address = place.get("address", "")
                rating  = place.get("rating", "")
                hours   = place.get("hours", "")
                phone   = place.get("phone", "")
                website = place.get("website", "")

                parts = [f"📍 {name}"]
                if address: parts.append(f"Address: {address}")
                if rating:  parts.append(f"Rating: {rating}★")
                if hours:   parts.append(f"Hours: {hours}")
                if phone:   parts.append(f"Phone: {phone}")
                if website: parts.append(f"Website: {website}")
                results.append("\n".join(parts))

            return "\n\n---\n\n".join(results)

    except Exception as exc:
        logger.error("Maps POI API failed", extra={"query": query[:50], "error": str(exc)})
        return ""


async def _web_search_fallback(query: str, lang: str = "en") -> str:
    return await _search(query, lang)


async def fetch_page(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text[:_MAX_CHARS]
    except Exception as exc:
        logger.error("Page fetch failed", extra={"url": url, "error": str(exc)})
        return ""


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "weather":             _weather,
    "search":              _search,
    "maps":                _maps,
    "maps_poi":            _maps_poi,
    "web_search":          _web_search_fallback,
    "web_search_fallback": _web_search_fallback,
}


async def run_tool(tool_name: str, params: dict, lang: str = "en") -> str:
    fn = _TOOL_MAP.get(tool_name)
    if fn is None:
        logger.warning("Unknown tool", extra={"tool": tool_name})
        return ""

    query = params.get("query", "")
    lang  = params.get("lang", lang)

    logger.info("Running tool", extra={"tool": tool_name, "query": query[:80]})
    result = await fn(query, lang)

    if not result:
        logger.warning("Tool returned empty result", extra={"tool": tool_name})

    return result