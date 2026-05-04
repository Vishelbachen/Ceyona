from __future__ import annotations

import logging
import re

from external.maps import maps_service
from external.search import search_service
from external.weather import weather_service

logger = logging.getLogger(__name__)


async def run_tool(
    tool_name: str,
    params: dict,
    lang: str = "en",
) -> str | None:
    """
    Dispatch to external tool.
    Returns result string or None on failure.
    None → orchestrator falls back to LLM.
    """
    try:
        # ── weather (current) ─────────────────────────────────────────────────
        if tool_name == "weather":
            city = re.sub(r"[^\w\s\-]", "", params.get("city", "")).strip()
            if not city:
                logger.warning("Weather: empty city")
                return None
            data = await weather_service.get_current(city=city, lang=lang)
            if not data:
                logger.warning("Weather: no data", extra={"city": city})
                return None
            return weather_service.format_current(data, lang=lang)

        # ── weather (forecast) ────────────────────────────────────────────────
        elif tool_name == "weather_forecast":
            city = re.sub(r"[^\w\s\-]", "", params.get("city", "")).strip()
            cnt  = int(params.get("cnt", 5))
            if not city:
                return None
            data = await weather_service.get_forecast(city=city, lang=lang, cnt=cnt)
            if not data:
                return None
            items = data.get("list", [])[:cnt]
            lines = []
            for item in items:
                dt   = item.get("dt_txt", "")
                temp = item.get("main", {}).get("temp", "?")
                desc = ""
                w    = item.get("weather", [])
                if w:
                    desc = w[0].get("description", "")
                lines.append(f"{dt}: {temp}°C, {desc}")
            return "\n".join(lines) if lines else None

        # ── maps (geocode — toponym / address lookup) ─────────────────────────
        elif tool_name in ("maps", "geocode"):
            query = params.get("query", "").strip()
            if not query:
                return None
            feature = await maps_service.geocode(query=query, lang=lang)
            if not feature:
                return maps_service.format_not_found(lang)
            return maps_service.format_geocode(feature, lang=lang)

        # ── maps_poi (nearest place by category) ─────────────────────────────
        elif tool_name == "maps_poi":
            category = params.get("category", "").strip()
            location = params.get("location", "").strip()

            if not category:
                logger.warning("maps_poi: empty category", extra={"params": params})
                return None

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

        # ── search ────────────────────────────────────────────────────────────
        elif tool_name == "search":
            query = params.get("query", "").strip()
            num   = int(params.get("num", 5))
            if not query:
                return None
            results = await search_service.search(query=query, lang=lang, num=num)
            if not results:
                return None
            return search_service.format_results(results, lang=lang)

        else:
            logger.warning("Unknown tool", extra={"tool_name": tool_name})
            return None

    except Exception as exc:
        import traceback
        logger.error("run_tool failed: %s\n%s", str(exc), traceback.format_exc())
        return None