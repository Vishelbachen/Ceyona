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


def _split_poi_query(query: str) -> tuple[str, str]:
    """
    Split a POI query into (category, location).
    Handles patterns like:
      "дешёвые отели в центре Воронежа"  → ("дешёвые отели", "центре Воронежа")
      "restaurants in Rome city center"  → ("restaurants", "Rome city center")
      "günstige Hotels in Berlin Mitte"  → ("günstige Hotels", "Berlin Mitte")
      "رستوران در تهران"                 → ("رستوران", "تهران")
    Falls back to (query, query) so Mapbox still tries something.
    """
    import re
    q = query.strip()

    # Multilingual "X in/в/в/im/à/en/a/da/de/в Y" pattern
    m = re.search(
        r"^(.+?)\s+(?:in|в|у|im|à|en|a\s+|da\s+|de\s+|في|در|在|で|에서)\s+(.+)$",
        q, re.IGNORECASE
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Georgian: "X თბილისში / X-ში"
    m = re.search(r"^(.+?)\s+(.+?(?:ში|ზე|ში))$", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Korean: "X 서울에서" / "서울 X"
    m = re.search(r"^(.+?)\s+(.+에서?)$", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Fallback: use whole query for both — Mapbox will do its best
    return q, q


async def _maps_poi(query: str, lang: str = "en") -> str:
    from external.maps import maps_service
    category, location = _split_poi_query(query)
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
    Covers: ru, uk, en, de, fr, es, pt, it, tr, ar, zh, ja, ko, ka, hy, az, kk, uz, fa, pl, nl, sv, fi.
    """
    import re
    q = query.strip()

    # Russian/Ukrainian: "от/из/с X до/в/к Y"
    m = re.search(r"(?:від|з|від|от|из|с)\s+(.+?)\s+(?:до|в|к|на|у)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
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

    # French: "de X à Y" / "depuis X jusqu'à Y"
    m = re.search(r"(?:de|depuis)\s+(.+?)\s+(?:à|jusqu'à|jusqu'a|au|en)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Spanish/Portuguese: "de X a Y" / "desde X hasta Y"
    m = re.search(r"(?:desde|de)\s+(.+?)\s+(?:hasta|a)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Italian: "da X a Y"
    m = re.search(r"da\s+(.+?)\s+a\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Turkish: "X'den Y'e" / "X'tan Y'a" (simplified: X'[a-z]+ Y'[a-z]+)
    m = re.search(r"(.+?)'[a-züğışçö]+\s+(.+?)'[a-züğışçö]+(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Polish: "z X do Y"
    m = re.search(r"(?:z|ze)\s+(.+?)\s+(?:do|na)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Dutch: "van X naar Y"
    m = re.search(r"van\s+(.+?)\s+naar\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Swedish/Norwegian/Danish: "från/fra X till/til Y"
    m = re.search(r"(?:från|fra)\s+(.+?)\s+(?:till|til)\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Finnish: "X:sta Y:ään" — too complex; use keyword "miten päästä X:stä Y:hyn" → skip, fallback ok

    # Georgian: "X-იდან [nav words] Y-ში" / "X-დან Y-ში"
    # Strip navigation verb phrases before matching suffixes
    q_ka = re.sub(r'\s*(?:როგორ\s+(?:მივიდე|წავიდე|მოვიდე|ჩავიდე)|მარშრუტი|გზა)\s*', ' ', q).strip()
    m = re.search(r"(.+?)(?:იდან|დან|ისგან)\s+(.+?)(?:ში|ზე|ამდე)(?:\?|$)", q_ka)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Armenian: "X-ից Y"
    m = re.search(r"(.+?)ից\s+(.+?)(?:\?|$)", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Azerbaijani: "X-dən Y-ə"
    m = re.search(r"(.+?)(?:dən|dan|dən)\s+(.+?)(?:ə|a|ya|yə)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Kazakh/Uzbek: "X-дан Y-ға" / "X-dan Y-ga"
    m = re.search(r"(.+?)(?:дан|ден|dan|den)\s+(.+?)(?:ға|ге|га|га|ga|ge)(?:\?|$)", q, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Persian/Farsi: "از X به Y"
    m = re.search(r"از\s+(.+?)\s+به\s+(.+?)(?:\?|$)", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Arabic: "من X إلى Y"
    m = re.search(r"من\s+(.+?)\s+(?:إلى|الى|لـ)\s+(.+?)(?:\?|$)", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Chinese: "从X到Y" / "由X去Y"
    m = re.search(r"(?:从|由)\s*(.+?)\s*(?:到|去|至)\s*(.+?)(?:\?|？|$)", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Japanese: "XからYまで" / "XからYへ"
    m = re.search(r"(.+?)から\s*(.+?)(?:まで|へ|に)(?:\?|？|$)", q)
    if m:
        return m.group(1).strip(), m.group(2).strip()

    # Korean: "X에서 Y까지" / "X에서 Y로"
    m = re.search(r"(.+?)에서\s+(.+?)(?:까지|로|으로)(?:\?|？|$)", q)
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