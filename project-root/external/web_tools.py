from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────
# Imports are lazy (inside each function) so that a startup failure in one
# external service does NOT kill the entire tool dispatcher.
# Previously top-level imports meant search.py crashing → web_tools.py dead →
# ALL tools unavailable, not just search.

async def _weather(query: str, lang: str = "en") -> str:
    from external.weather import weather_service, _extract_city
    city = _extract_city(query)
    if not city:
        return ""
    data = await weather_service.get_current(city, lang=lang)
    if not data:
        return ""
    return weather_service.format_current(data, lang=lang)


async def _search(query: str, lang: str = "en") -> str:
    from external.search import search_service
    results = await search_service.search(query, lang=lang)
    return search_service.format_results(results, lang=lang)


async def _maps(query: str, lang: str = "en") -> str:
    from external.maps import maps_service, _extract_location
    location = _extract_location(query)
    feature = await maps_service.geocode(location or query, lang=lang)
    if not feature:
        return maps_service.format_not_found(lang=lang)
    return maps_service.format_geocode(feature, lang=lang)


async def _maps_poi(query: str, lang: str = "en") -> str:
    from external.maps import maps_service
    feature = await maps_service.search_poi(
        category=query,
        location=query,
        lang=lang,
    )
    if not feature:
        return maps_service.format_poi_not_found(
            category=query,
            location="",
            lang=lang,
        )
    return maps_service.format_poi(feature, lang=lang)


async def _web_search_fallback(query: str, lang: str = "en") -> str:
    return await _search(query, lang)


async def _maps_route(query: str, lang: str = "en") -> str:
    """
    Build a driving route between two locations using Mapbox Directions API.

    Expects query like "от аэропорта Воронежа до центра" or "from X to Y".
    Extracts origin/destination then calls MapsService.get_route().
    Falls back to graceful not-found message on any failure.
    """
    from external.maps import maps_service
    origin, destination = _extract_route_endpoints(query, lang)

    if not origin or not destination:
        # Can't parse endpoints — fall back to web search for transport info
        return await _search(query, lang)

    route = await maps_service.get_route(origin=origin, destination=destination, lang=lang)
    if not route:
        return maps_service.format_route_not_found(lang=lang)

    return maps_service.format_route(route, lang=lang)


def _extract_route_endpoints(query: str, lang: str = "en") -> tuple[str, str]:
    """
    Extract (origin, destination) from a routing query.
    Returns ("", "") if parsing fails.
    """
    import re
    q = query.strip()

    # Russian: "от X до Y" / "из X в Y" / "с X до Y"
    m = re.search(r"(?:от|из|с)\s+(.+?)\s+(?:до|в|к)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # English: "from X to Y"
    m = re.search(r"from\s+(.+?)\s+to\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # German: "von X nach Y"
    m = re.search(r"von\s+(.+?)\s+nach\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return "", ""


# ─── DISPATCHER ───────────────────────────────────────────────────────────────

_TOOL_MAP = {
    "weather":             _weather,
    "search":              _search,
    "maps":                _maps,
    "maps_poi":            _maps_poi,
    "maps_route":          _maps_route,
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