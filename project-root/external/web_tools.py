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
            "Reply with a JSON object ONLY, no extra text, no markdown: "
            '{"category": "...", "location": ""}. '
            "RULES:\n"
            "1. category = what the user is looking for (e.g. 'cheap hotels', 'restaurants', 'pharmacies', 'ATMs').\n"
            "2. location = the FULL city or area name suitable for geocoding. "
            "Never return just 'center', 'downtown', 'центр', 'here'. "
            "Always return the actual city name, e.g. 'Voronezh', 'Saint Petersburg city center'.\n"
            "3. Include price qualifiers (cheap, budget, luxury, дешёвые) in category, NOT in location.\n"
            "4. If you cannot determine a field, use empty string \"\".\n"
            "Output JSON only. No explanation.\n\n"
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
            "Reply with a JSON object ONLY — no markdown, no explanation: "
            '{"origin": "...", "destination": "..."}. '
            "CRITICAL RULES:\n"
            "1. Both values MUST be FULL, geocodable place names — never vague words alone.\n"
            "2. Never output: center, центр, downtown, airport, station, вокзал, аэропорт — "
            "always add the CITY NAME. Examples: 'Voronezh Airport', 'Voronezh city center', "
            "'Moscow Sheremetyevo Airport', 'Saint Petersburg Moskovsky station'.\n"
            "3. If a city is named anywhere in the query — include it in BOTH origin AND destination.\n"
            "4. 'центр' → '[City] city center'. 'аэропорт' → '[City] Airport'.\n"
            "5. If you cannot determine a value — use empty string.\n"
            "Output JSON only.\n\n"
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