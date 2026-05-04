from __future__ import annotations

import logging
import re

from external.maps import maps_service
from external.search import search_service
from external.weather import weather_service

logger = logging.getLogger(__name__)


# ─── MAPS POI QUERY PARSER ────────────────────────────────────────────────────

# Maps common POI attribute keywords to category strings for the maps service.
# The parser strips these keywords from the query to extract the place name.

_POI_ATTRIBUTE_PATTERNS: tuple[tuple[re.Pattern, str], ...] = (
    # hours / open
    (re.compile(
        r"\b(opening hours?|opening times?|hours? of operation|business hours?|"
        r"what time does|what time do|is it open|is open now|opens? at|closes? at|"
        r"часы работы|режим работы|когда открывается|когда закрывается|"
        r"во сколько открывается|во сколько закрывается|"
        r"сейчас открыто|сейчас работает|работает сейчас|открыто сейчас|"
        r"öffnungszeiten|heures d.ouverture|horarios?|"
        r"orari di apertura|çalışma saatleri|ساعات العمل|营业时间|営業時間|영업시간)\b",
        re.IGNORECASE,
    ), "hours"),
    # phone / contact
    (re.compile(
        r"\b(phone number(?: of)?|contact number|номер телефона|как позвонить|"
        r"telefonnummer|numéro de téléphone|número de teléfono|"
        r"numero di telefono|telefon numarası|رقم الهاتف|电话号码|電話番号|전화번호)\b",
        re.IGNORECASE,
    ), "phone"),
    # rating / reviews
    (re.compile(
        r"\b(rating(?: of)?|reviews? of|how good is|is it worth|"
        r"рейтинг|отзывы|стоит ли идти|стоит посетить|"
        r"bewertung|rezensionen|avis sur|reseñas?|recensioni|yorumlar|"
        r"تقييم|مراجعات|评分|評分|評価|口コミ|평점|리뷰)\b",
        re.IGNORECASE,
    ), "rating"),
    # website
    (re.compile(
        r"\b(website(?: of)?|official website|офиц(?:иальный)? сайт|"
        r"webseite|site web|sitio web|sito web|web sitesi|الموقع الرسمي|官方网站|公式サイト|공식 웹사이트)\b",
        re.IGNORECASE,
    ), "website"),
    # price / admission
    (re.compile(
        r"\b(admission fee|entry fee|ticket price|price(?: of)?|"
        r"how much (?:does it cost|to get in)|"
        r"цена входа|стоимость билета|сколько стоит вход|стоимость посещения|"
        r"eintrittspreise|prix d.entr.e|precio de entrada|preço de entrada|"
        r"prezzo di ingresso|giriş ücreti|سعر الدخول|入场费|入場料|입장료)\b",
        re.IGNORECASE,
    ), "price"),
)

_POI_STRIP_PATTERNS: tuple[re.Pattern, ...] = tuple(
    p for p, _ in _POI_ATTRIBUTE_PATTERNS
)


def _parse_poi_params(query: str, lang: str) -> dict:
    """
    Extract category and location from a free-form POI query.

    Strategy:
      1. Detect which attribute is being asked about (hours/phone/rating/etc.)
      2. Strip attribute keywords from query to get the place name / location
      3. Return {query, category, location, lang} for maps_service.search_poi
    """
    cleaned = query
    detected_category = "place"  # default

    for pattern, category in _POI_ATTRIBUTE_PATTERNS:
        if pattern.search(cleaned):
            detected_category = category
            cleaned = pattern.sub("", cleaned)
            break  # first match wins

    # Strip common filler words
    filler = re.compile(
        r"\b(of|the|a|an|its|their|this|that|в|о|об|на|для|это|тот|та)\b",
        re.IGNORECASE,
    )
    cleaned = filler.sub(" ", cleaned).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ?,.")

    location = cleaned if cleaned else query

    return {
        "query": query,
        "category": detected_category,
        "location": location,
        "lang": lang,
    }


# ─── TOOL RUNNER ──────────────────────────────────────────────────────────────

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
            # Support both explicit city param and full query string
            city = params.get("city", "").strip()
            if not city:
                # Extract city from query if city not explicitly provided
                query = params.get("query", "").strip()
                city = re.sub(
                    r"(weather|погода|прогноз|forecast|temperatura|температура"
                    r"|wetter|météo|clima|meteo|hava durumu|الطقس|天气|天氣|天気|날씨"
                    r"|ამინდი|եղանակ|ob-havo|ауа райы|yağış)\s*",
                    "", query, flags=re.IGNORECASE,
                ).strip(" ?,.")
            city = re.sub(r"[^\w\s\-]", "", city).strip()
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
            city = params.get("city", "").strip()
            cnt  = int(params.get("cnt", 5))
            if not city:
                query = params.get("query", "").strip()
                city = re.sub(
                    r"(forecast|прогноз на|погода на)\s*", "", query,
                    flags=re.IGNORECASE,
                ).strip()
            city = re.sub(r"[^\w\s\-]", "", city).strip()
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

        # ── maps (geocode) ────────────────────────────────────────────────────
        elif tool_name in ("maps", "geocode"):
            query = params.get("query", "").strip()
            if not query:
                return None
            feature = await maps_service.geocode(query=query, lang=lang)
            if not feature:
                return maps_service.format_not_found(lang)
            return maps_service.format_geocode(feature, lang=lang)

        # ── maps_poi ──────────────────────────────────────────────────────────
        elif tool_name == "maps_poi":
            # Support both pre-parsed params and raw query
            category = params.get("category", "").strip()
            location = params.get("location", "").strip()

            # If intent_engine passed raw query, parse it here
            if not category:
                raw_query = params.get("query", "").strip()
                if not raw_query:
                    logger.warning("maps_poi: no query or category", extra={"params": params})
                    return None
                parsed = _parse_poi_params(raw_query, lang)
                category = parsed["category"]
                location = parsed["location"]

            if not category:
                logger.warning("maps_poi: empty category after parsing", extra={"params": params})
                return None

            logger.info("maps_poi dispatch", extra={
                "category": category,
                "location": location,
            })

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
