from __future__ import annotations

import logging
import re

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_MAX_CHARS = 5000


# ─── INDIVIDUAL TOOL IMPLEMENTATIONS ─────────────────────────────────────────

async def _weather(query: str, lang: str = "en") -> str:
    """Fetch real weather data from OpenWeatherMap."""
    if not settings.openweather_api_key:
        return ""

    # extract city name from query
    city = _extract_city(query)
    if not city:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": city,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                    "lang": lang,
                },
            )
            r.raise_for_status()
            d = r.json()

            name    = d.get("name", city)
            country = d.get("sys", {}).get("country", "")
            temp    = d["main"]["temp"]
            feels   = d["main"]["feels_like"]
            desc    = d["weather"][0]["description"]
            humid   = d["main"]["humidity"]
            wind    = d["wind"]["speed"]

            return (
                f"Weather in {name}, {country}:\n"
                f"Temperature: {temp:.1f}°C (feels like {feels:.1f}°C)\n"
                f"Conditions: {desc}\n"
                f"Humidity: {humid}%\n"
                f"Wind: {wind} m/s"
            )
    except Exception as exc:
        logger.error("Weather API failed", extra={"city": city, "error": str(exc)})
        return ""


async def _search(query: str, lang: str = "en") -> str:
    """Search the web via SerpAPI."""
    if not settings.serpapi_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": settings.serpapi_key,
                    "num": 5,
                    "engine": "google",
                    "hl": lang,
                },
            )
            r.raise_for_status()
            data = r.json()

            results = []

            # answer box (direct answer)
            ab = data.get("answer_box", {})
            if ab.get("answer"):
                results.append(f"Direct answer: {ab['answer']}")
            elif ab.get("snippet"):
                results.append(f"Direct answer: {ab['snippet']}")

            # knowledge graph
            kg = data.get("knowledge_graph", {})
            if kg.get("description"):
                results.append(f"Summary: {kg['description']}")

            # organic results
            for item in data.get("organic_results", [])[:5]:
                title   = item.get("title", "")
                snippet = item.get("snippet", "")
                link    = item.get("link", "")
                if snippet:
                    results.append(f"{title}: {snippet}\nSource: {link}")

            return "\n\n".join(results)[:_MAX_CHARS]

    except Exception as exc:
        logger.error("Search API failed", extra={"query": query, "error": str(exc)})
        return ""


async def _maps(query: str, lang: str = "en") -> str:
    """Geocode a location via Mapbox."""
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
                    "limit": 1,
                    "language": lang,
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
                f"Location: {name}\n"
                f"Coordinates: {lat:.6f}°N, {lon:.6f}°E\n"
                f"Google Maps: https://maps.google.com/?q={lat},{lon}"
            )
    except Exception as exc:
        logger.error("Maps API failed", extra={"query": query, "error": str(exc)})
        return ""


async def _maps_poi(query: str, lang: str = "en") -> str:
    """Search points of interest via SerpAPI Google Maps."""
    if not settings.serpapi_key:
        return ""

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_maps",
                    "q": query,
                    "api_key": settings.serpapi_key,
                    "hl": lang,
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

                parts = [name]
                if address: parts.append(f"Address: {address}")
                if rating:  parts.append(f"Rating: {rating}★")
                if hours:   parts.append(f"Hours: {hours}")
                if phone:   parts.append(f"Phone: {phone}")
                if website: parts.append(f"Website: {website}")
                results.append("\n".join(parts))

            return "\n\n".join(results)

    except Exception as exc:
        logger.error("Maps POI API failed", extra={"query": query, "error": str(exc)})
        return ""


async def _web_search_fallback(query: str, lang: str = "en") -> str:
    """
    Generic web search for QUESTION intent when retrieval has no data.
    Same as _search but used as grounding fallback.
    """
    return await _search(query, lang)


async def fetch_page(url: str) -> str:
    """Fetch raw text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text[:_MAX_CHARS]
    except Exception as exc:
        logger.error("Page fetch failed", extra={"url": url, "error": str(exc)})
        return ""


# ─── CITY / LOCATION EXTRACTION ──────────────────────────────────────────────

_WEATHER_PREPS = (
    "in ", "в ", "для ", "for ", "at ", "dans ", "en ", "in ",
    "für ", "для города ", "city ", "город ",
)


def _extract_city(query: str) -> str:
    """Extract city name from weather query."""
    lower = query.lower()
    for prep in _WEATHER_PREPS:
        idx = lower.find(prep)
        if idx != -1:
            city = query[idx + len(prep):].strip()
            city = re.split(r"[?,\n]", city)[0].strip()
            if city:
                return city
    # fallback: last word(s)
    words = query.strip().split()
    return " ".join(words[-2:]) if len(words) >= 2 else query.strip()


def _extract_location(query: str) -> str:
    """Extract location from maps query."""
    lower = query.lower()
    for kw in ("where is", "location of", "address of", "where are",
               "где находится", "адрес", "покажи на карте",
               "como llegar a", "wo ist", "où est"):
        idx = lower.find(kw)
        if idx != -1:
            loc = query[idx + len(kw):].strip()
            loc = re.split(r"[?,\n]", loc)[0].strip()
            if loc:
                return loc
    return query.strip()


# ─── MAIN DISPATCHER ─────────────────────────────────────────────────────────

_TOOL_MAP = {
    "weather":   _weather,
    "search":    _search,
    "maps":      _maps,
    "maps_poi":  _maps_poi,
    "web_search": _web_search_fallback,
}


async def run_tool(tool_name: str, params: dict, lang: str = "en") -> str:
    """
    Main entry point called by orchestrator._run_tool().
    Dispatches to the correct tool implementation.
    Returns empty string on failure — orchestrator handles fallback.
    """
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