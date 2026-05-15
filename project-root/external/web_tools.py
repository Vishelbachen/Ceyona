from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────
# Imports are lazy (inside each function) so that a startup failure in one
# external service does NOT kill the entire tool dispatcher.

async def _weather(query: str, lang: str = "en") -> str:
    from external.weather import weather_service, _extract_city
    city = await _extract_city(query)
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
    from external.maps import maps_service
    # Pass query directly to Mapbox; it handles any language natively.
    feature = await maps_service.geocode(query, lang=lang)
    if not feature:
        return maps_service.format_not_found(lang=lang)
    return maps_service.format_geocode(feature, lang=lang)


async def _extract_poi_parts_via_llm(query: str) -> tuple[str, str]:
    """
    Use Groq to extract (category, location) from a POI query.
    Falls back to (query, query) so Mapbox still tries something.
    """
    try:
        from llm.groq_client import groq_client
        prompt = (
            "Extract the POI category and location from the following query. "
            "Reply with a JSON object only, no extra text: "
            '{"category": "...", "location": "..."}. '
            "category = what the user is looking for (e.g. 'cheap hotels', 'restaurants', 'pharmacies'). "
            "location = the full city/area name for geocoding (e.g. 'Voronezh', 'Rome city center'). "
            "Always include the city name in location — never return just 'center' or 'downtown'. "
            "Include any price qualifier (cheap, budget, luxury) in category, not in location. "
            "If you cannot determine one of the fields, use an empty string.\n\n"
            f"Query: {query}"
        )
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        raw = response.text
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        category = data.get("category", "").strip()
        location = data.get("location", "").strip()
        if category or location:
            return category or query, location or query
    except Exception as exc:
        logger.warning("_extract_poi_parts_via_llm failed", extra={"error": str(exc)})

    # Cheap regex fallback: "X in/в/im/à/en/a Y"
    import re
    m = re.search(
        r"^(.+?)\s+(?:in|в|im|à|en|a|di|в)\s+(.+)$",
        query.strip(), re.IGNORECASE
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()

    return query, query


async def _maps_poi(query: str, lang: str = "en") -> str:
    from external.maps import maps_service
    category, location = await _extract_poi_parts_via_llm(query)
    feature = await maps_service.search_poi(
        category=category,
        location=location,
        lang=lang,
    )
    if not feature:
        return maps_service.format_poi_not_found(
            category=category,
            location=location,
            lang=lang,
        )
    return maps_service.format_poi(feature, lang=lang)


async def _web_search_fallback(query: str, lang: str = "en") -> str:
    return await _search(query, lang)


async def _extract_route_endpoints_via_llm(query: str) -> tuple[str, str]:
    """
    Use Groq to extract (origin, destination) from a routing query.
    No regex, no language branches — the LLM handles all languages.
    Returns ("", "") if extraction fails.
    """
    try:
        from llm.groq_client import groq_client
        prompt = (
            "Extract the origin and destination from the following routing query. "
            "Reply with a JSON object only, no extra text: "
            '{"origin": "...", "destination": "..."}. '
            "IMPORTANT: always produce FULL, unambiguous place names suitable for geocoding. "
            "If the query mentions a city, include it in both fields. "
            "Never return vague words like 'center', 'центр', 'downtown', 'airport' alone — "
            "always attach the city name, e.g. 'Voronezh city center', 'Voronezh Airport'. "
            "If the city is not mentioned explicitly but is clear from context (e.g. 'airport' "
            "in a query that already names a city), include the city anyway. "
            "If you cannot determine one of the fields, use an empty string.\n\n"
            f"Query: {query}"
        )
        response = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        raw = response.text
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        origin      = data.get("origin", "").strip()
        destination = data.get("destination", "").strip()
        return origin, destination
    except Exception as exc:
        logger.warning("_extract_route_endpoints_via_llm failed", extra={"error": str(exc)})
        return "", ""


async def _maps_route(query: str, lang: str = "en") -> str:
    """
    Build a driving route between two locations using Mapbox Directions API.
    Endpoint extraction is delegated to the LLM (Groq).
    """
    from external.maps import maps_service
    origin, destination = await _extract_route_endpoints_via_llm(query)

    if not origin or not destination:
        # Can't parse endpoints — fall back to web search for transport info
        return await _search(query, lang)

    route = await maps_service.get_route(origin=origin, destination=destination, lang=lang)
    if not route:
        return maps_service.format_route_not_found(lang=lang)

    return maps_service.format_route(route, lang=lang)


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