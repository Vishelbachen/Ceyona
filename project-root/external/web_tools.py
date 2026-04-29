import logging

from external.weather import weather_service
from external.maps import maps_service
from external.search import search_service

logger = logging.getLogger(__name__)


# ─── UNIFIED TOOL DISPATCHER ─────────────────────────────────────────────────
# Called by agent layer when tool use is required.
# No business logic. Pure routing.

async def run_tool(
    tool_name: str,
    params: dict,
    lang: str = "en",
) -> str:
    """
    Dispatch to the correct external tool.
    Returns formatted string ready for LLM context or direct reply.

    Supported tools:
        weather         — params: {"city": str}
        weather_forecast — params: {"city": str, "cnt": int}
        geocode         — params: {"query": str}
        search          — params: {"query": str, "num": int}
    """
    try:
        if tool_name == "weather":
            city = params.get("city", "")
            if not city:
                return _err("No city provided", lang)
            data = await weather_service.get_current(city=city, lang=lang)
            if not data:
                return _err("Weather data unavailable", lang)
            return weather_service.format_current(data, lang=lang)

        elif tool_name == "weather_forecast":
            city = params.get("city", "")
            cnt = int(params.get("cnt", 5))
            if not city:
                return _err("No city provided", lang)
            data = await weather_service.get_forecast(city=city, lang=lang, cnt=cnt)
            if not data:
                return _err("Forecast unavailable", lang)
            # Return raw summary — LLM will format narrative
            items = data.get("list", [])[:cnt]
            lines = []
            for item in items:
                dt = item.get("dt_txt", "")
                temp = item.get("main", {}).get("temp", "?")
                desc = ""
                w = item.get("weather", [])
                if w:
                    desc = w[0].get("description", "")
                lines.append(f"{dt}: {temp}°C, {desc}")
            return "\n".join(lines) if lines else _err("No forecast data", lang)

        elif tool_name == "geocode":
            query = params.get("query", "")
            if not query:
                return _err("No query provided", lang)
            feature = await maps_service.geocode(query=query, lang=lang)
            if not feature:
                return _err("Location not found", lang)
            return maps_service.format_geocode(feature, lang=lang)

        elif tool_name == "search":
            query = params.get("query", "")
            num = int(params.get("num", 5))
            if not query:
                return _err("No query provided", lang)
            results = await search_service.search(query=query, lang=lang, num=num)
            return search_service.format_results(results, lang=lang)

        else:
            logger.warning("Unknown tool", extra={"tool_name": tool_name})
            return _err(f"Unknown tool: {tool_name}", lang)

    except Exception as exc:
        logger.error("run_tool failed", extra={
            "tool": tool_name,
            "error": str(exc),
        })
        return _err("Tool execution failed", lang)


def _err(msg: str, lang: str) -> str:
    _prefix: dict[str, str] = {
        "en": "⚠️ Error",
        "ru": "⚠️ Ошибка",
        "de": "⚠️ Fehler",
        "fr": "⚠️ Erreur",
        "es": "⚠️ Error",
        "pt": "⚠️ Erro",
        "it": "⚠️ Errore",
        "tr": "⚠️ Hata",
        "ar": "⚠️ خطأ",
        "zh": "⚠️ 错误",
        "ja": "⚠️ エラー",
        "ko": "⚠️ 오류",
        "pl": "⚠️ Błąd",
        "uk": "⚠️ Помилка",
        "fa": "⚠️ خطا",
    }
    prefix = _prefix.get(lang, _prefix["en"])
    return f"{prefix}: {msg}"