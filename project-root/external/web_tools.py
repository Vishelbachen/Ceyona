from __future__ import annotations

import json
import logging
from collections.abc import Mapping

from i18n.t import t as _t

logger = logging.getLogger(__name__)


def _pick(params: Mapping[str, object], *keys: str, default: str = "") -> str:
    for key in keys:
        value = params.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


# ─── TOOL IMPLEMENTATIONS ─────────────────────────────────────────────────────
# Imports are lazy (inside each function) so that a startup failure in one
# external service does NOT kill the entire tool dispatcher.

async def _weather(params: Mapping[str, object], lang: str = "en") -> str:
    from external.weather import _extract_city, weather_service

    query = _pick(params, "query", "city")
    if not query:
        return ""

    city = await _extract_city(query)
    if not city:
        return ""

    data = await weather_service.get_current(city, lang=lang)
    if not data:
        return ""

    return weather_service.format_current(data, lang=lang)


async def _search(params: Mapping[str, object], lang: str = "en") -> str:
    # Query is already rewritten by _understand_query() in intent_engine.classify().
    # web_tools receives the final search query — no transformation needed here.
    from external.search import search_service

    query = _pick(params, "query")
    if not query:
        return ""

    results = await search_service.search(query, lang=lang)
    return search_service.format_results(results, lang=lang)


async def _maps(params: Mapping[str, object], lang: str = "en") -> str:
    from external.maps import maps_service

    # Pass query directly to Mapbox; it handles any language natively.
    query = _pick(params, "query", "location", "place")
    if not query:
        return ""

    feature = await maps_service.geocode(query, lang=lang)
    if not feature:
        return maps_service.format_not_found(lang=lang)
    return maps_service.format_geocode(feature, lang=lang)


async def _extract_poi_parts_via_llm(query: str) -> tuple[str, str, bool]:
    """
    Use Groq to extract (category, location) from a POI query.
    Returns (category, location, is_navigation).

    is_navigation=True means the LLM determined this is a routing/transit query,
    not a POI lookup. The caller redirects to _search() in that case.
    This is the language-agnostic guard: works for all 75 lingua languages
    without any hardcoded signal strings.

    Falls back to (query, query, False) on LLM/parse failure so the caller
    can still attempt a Mapbox search rather than silently failing.
    """
    try:
        from llm.groq_client import groq_client
        prompt = (
            "Analyze the following query and reply with a JSON object ONLY — "
            "no markdown, no explanation.\n\n"
            "If the query asks HOW TO GET FROM one place TO ANOTHER "
            "(navigation, directions, transit, transport, routes, travel time, distance between two points): "
            'reply {"is_navigation": true, "category": "", "location": ""}.\n\n'
            "Otherwise extract the POI category and location:\n"
            '{"is_navigation": false, "category": "...", "location": "..."}\n\n'
            "RULES for category/location (only when is_navigation=false):\n"
            "1. category = what the user is looking for (e.g. 'cheap hotels', 'restaurants', 'pharmacies', 'ATMs').\n"
            "2. location = the FULL city or area name suitable for geocoding. "
            "Never return just 'center', 'downtown', 'центр', 'here'. "
            "Always return the actual city name, e.g. 'Voronezh', 'Saint Petersburg city center'.\n"
            "3. Include price qualifiers (cheap, budget, luxury, дешёвые) in category, NOT in location.\n"
            "4. If you cannot determine a field, use empty string "".\n"
            "Output JSON only.\n\n"
            f"Query: {query}"
        )
        response = await groq_client.complete(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        raw = response.text
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)

        if data.get("is_navigation"):
            logger.info(
                "_extract_poi_parts_via_llm: navigation intent detected — redirecting to search",
                extra={"query": query[:80]},
            )
            return "", "", True

        category = data.get("category", "").strip()
        location = data.get("location", "").strip()
        if category or location:
            return category or query, location or query, False

    except Exception as exc:
        logger.warning("_extract_poi_parts_via_llm failed", extra={"error": str(exc)})

    # Cheap regex fallback: "X in/в/im/à/en/a Y"
    import re
    m = re.search(
        r"^(.+?)\s+(?:in|в|im|à|en|a|di|в)\s+(.+)$",
        query.strip(), re.IGNORECASE
    )
    if m:
        return m.group(1).strip(), m.group(2).strip(), False

    return query, query, False


async def _maps_poi(params: Mapping[str, object], lang: str = "en") -> str:
    from external.maps import maps_service

    query = _pick(params, "query")
    category = _pick(params, "category")
    location = _pick(params, "location")

    if category and location:
        pass
    elif query:
        category, location, is_navigation = await _extract_poi_parts_via_llm(query)
        if is_navigation:
            logger.info(
                "_maps_poi: navigation query misrouted as POI — redirecting to search",
                extra={"query": query[:80], "lang": lang},
            )
            return await _search({"query": query}, lang)
    else:
        return _t("need_city_or_area", lang)

    feature = await maps_service.search_poi(
        category=category or query,
        location=location or query,
        lang=lang,
    )
    if not feature:
        return maps_service.format_poi_not_found(
            category=category or query,
            location=location or query,
            lang=lang,
        )
    return maps_service.format_poi(feature, lang=lang)


async def _web_search_fallback(params: Mapping[str, object], lang: str = "en") -> str:
    return await _search(params, lang)


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
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        raw = response.text
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        origin = data.get("origin", "").strip()
        destination = data.get("destination", "").strip()
        return origin, destination
    except Exception as exc:
        logger.warning("_extract_route_endpoints_via_llm failed", extra={"error": str(exc)})
        return "", ""


async def _maps_route(params: Mapping[str, object], lang: str = "en") -> str:
    """
    Build a driving route between two locations using Mapbox Directions API.
    Endpoint extraction is delegated to the LLM (Groq) only when structured
    origin/destination fields are not already provided.
    """
    from external.maps import maps_service

    origin = _pick(params, "origin")
    destination = _pick(params, "destination")
    query = _pick(params, "query")

    if (not origin or not destination) and query:
        origin, destination = await _extract_route_endpoints_via_llm(query)

    if not origin or not destination:
        return _t("need_route_origin", lang)

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
    "web_search_fallback":  _web_search_fallback,
}


async def run_tool(tool_name: str, params: dict | None, lang: str = "en") -> str:
    fn = _TOOL_MAP.get(tool_name)
    if fn is None:
        logger.warning("Unknown tool", extra={"tool": tool_name})
        return ""

    safe_params: Mapping[str, object] = params or {}
    call_lang = _pick(safe_params, "lang", default=lang)

    logger.info("Running tool", extra={
        "tool": tool_name,
        "query": _pick(safe_params, "query")[:80],
    })
    result = await fn(safe_params, call_lang)

    if not result:
        logger.warning("Tool returned empty result", extra={"tool": tool_name})

    return result