from __future__ import annotations

import logging
import re

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


# ─── LOCATION EXTRACTOR ───────────────────────────────────────────────────────

def _extract_location(query: str) -> str:
    """Extract location name from a maps query in any language."""
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
            loc = __import__('re').split(r"[?,\n]", loc)[0].strip()
            if loc:
                return loc
    return query.strip()


_BASE_URL       = "https://api.mapbox.com/geocoding/v5/mapbox.places"
_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"
_TIMEOUT        = 10.0

# ─── QUERY VALIDATION ─────────────────────────────────────────────────────────

_QUERY_MIN_LEN  = 3
_QUERY_MAX_LEN  = 256

# Patterns that indicate the text is NOT a real location query.
# These are rhetorical questions, complaints, or meta-questions that happen
# to contain maps vocabulary (e.g. "координаты дать не можешь?").
_RHETORICAL_PATTERNS: tuple[str, ...] = (
    # Russian
    "не можешь", "не можете", "не умеешь", "не умеете",
    "в смысле", "что за", "зачем мне", "на что мне",
    "почему не", "ты что", "ты вообще", "это что",
    "серьёзно", "серьезно", "издеваешься",
    # English
    "can't you", "cannot you", "why can't", "why can you",
    "what do you mean", "are you serious",
    "you can't even", "you don't even",
    # Generic
    "seriously", "wtf", "смысле",
)

# A real location query must contain at least one non-trivial token
# that could plausibly be a place name or geographic term.
# Queries consisting entirely of stop-words are rejected.
_QUERY_STOP_ONLY: frozenset[str] = frozenset({
    "here", "there", "this", "that", "it", "me", "my", "your",
    "тут", "там", "это", "моё", "мой", "моя", "твой", "твоя",
})


def _validate_query(query: str) -> bool:
    """
    Return True if the query looks like a real location request.

    Rejects:
      - too short / too long
      - rhetorical / complaint sentences
      - queries composed entirely of stop-words
    """
    stripped = query.strip()

    if len(stripped) < _QUERY_MIN_LEN or len(stripped) > _QUERY_MAX_LEN:
        return False

    lower = stripped.lower()

    if any(pattern in lower for pattern in _RHETORICAL_PATTERNS):
        logger.warning(
            "geocode: query rejected (rhetorical pattern)",
            extra={"query": stripped[:80]},
        )
        return False

    # Check that at least one token is not a pure stop-word
    tokens = re.findall(r"\w+", lower)
    meaningful = [t for t in tokens if t not in _QUERY_STOP_ONLY and len(t) > 1]
    if not meaningful:
        logger.warning(
            "geocode: query rejected (only stop-words)",
            extra={"query": stripped[:80]},
        )
        return False

    return True


# ─── LANGUAGE MAP ─────────────────────────────────────────────────────────────

_MB_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh", "ja": "ja", "ko": "ko",
    "pl": "pl", "uk": "uk", "nl": "nl", "sv": "sv",
    "da": "da", "fi": "fi", "cs": "cs", "ro": "ro",
    "hu": "hu", "he": "he", "vi": "vi", "th": "th",
    "id": "id", "ms": "ms",
}


def _mb_lang(lang: str) -> str:
    return _MB_LANG_MAP.get(lang, "en")


# ─── RESPONSE TEMPLATES ───────────────────────────────────────────────────────

_COORD_LABELS: dict[str, str] = {
    "en": "📍 *{name}*\nCoordinates: {lat}, {lon}",
    "ru": "📍 *{name}*\nКоординаты: {lat}, {lon}",
    "de": "📍 *{name}*\nKoordinaten: {lat}, {lon}",
    "fr": "📍 *{name}*\nCoordonnées : {lat}, {lon}",
    "es": "📍 *{name}*\nCoordenadas: {lat}, {lon}",
    "pt": "📍 *{name}*\nCoordenadas: {lat}, {lon}",
    "it": "📍 *{name}*\nCoordinate: {lat}, {lon}",
    "tr": "📍 *{name}*\nKoordinatlar: {lat}, {lon}",
    "ar": "📍 *{name}*\nالإحداثيات: {lat}, {lon}",
    "zh": "📍 *{name}*\n坐标：{lat}, {lon}",
    "ja": "📍 *{name}*\n座標：{lat}, {lon}",
    "ko": "📍 *{name}*\n좌표: {lat}, {lon}",
    "pl": "📍 *{name}*\nWspółrzędne: {lat}, {lon}",
    "uk": "📍 *{name}*\nКоординати: {lat}, {lon}",
    "nl": "📍 *{name}*\nCoördinaten: {lat}, {lon}",
    "sv": "📍 *{name}*\nKoordinater: {lat}, {lon}",
    "da": "📍 *{name}*\nKoordinater: {lat}, {lon}",
    "fi": "📍 *{name}*\nKoordinaatit: {lat}, {lon}",
    "cs": "📍 *{name}*\nSouřadnice: {lat}, {lon}",
    "ro": "📍 *{name}*\nCoordonate: {lat}, {lon}",
    "hu": "📍 *{name}*\nKoordináták: {lat}, {lon}",
    "he": "📍 *{name}*\nקואורדינטות: {lat}, {lon}",
    "vi": "📍 *{name}*\nTọa độ: {lat}, {lon}",
    "th": "📍 *{name}*\nพิกัด: {lat}, {lon}",
    "id": "📍 *{name}*\nKoordinat: {lat}, {lon}",
    "ms": "📍 *{name}*\nKoordinat: {lat}, {lon}",
    "ka": "📍 *{name}*\nკოორდინატები: {lat}, {lon}",
    "hy": "📍 *{name}*\nՀամակարգային կոորդինատներ: {lat}, {lon}",
    "az": "📍 *{name}*\nKoordinatlar: {lat}, {lon}",
    "kk": "📍 *{name}*\nКоординаттар: {lat}, {lon}",
    "uz": "📍 *{name}*\nKoordinatalar: {lat}, {lon}",
    "hi": "📍 *{name}*\nनिर्देशांक: {lat}, {lon}",
    "bn": "📍 *{name}*\nনির্দেশাঙ্ক: {lat}, {lon}",
    "ur": "📍 *{name}*\nنقاط: {lat}, {lon}",
    "fa": "📍 *{name}*\nمختصات: {lat}, {lon}",
    "mn": "📍 *{name}*\nКоординат: {lat}, {lon}",
    "sw": "📍 *{name}*\nUratibu: {lat}, {lon}",
}

_NOT_FOUND: dict[str, str] = {
    "en": "📍 Location not found. Try a more specific name.",
    "ru": "📍 Место не найдено. Попробуйте уточнить название.",
    "de": "📍 Ort nicht gefunden. Versuche einen genaueren Namen.",
    "fr": "📍 Lieu introuvable. Essayez un nom plus précis.",
    "es": "📍 Lugar no encontrado. Intenta con un nombre más específico.",
    "pt": "📍 Local não encontrado. Tente um nome mais específico.",
    "it": "📍 Luogo non trovato. Prova con un nome più specifico.",
    "tr": "📍 Konum bulunamadı. Daha spesifik bir isim deneyin.",
    "ar": "📍 الموقع غير موجود. جرّب اسماً أكثر تحديداً.",
    "zh": "📍 未找到该位置。请尝试更具体的名称。",
    "ja": "📍 場所が見つかりませんでした。より具体的な名前を試してください。",
    "ko": "📍 위치를 찾을 수 없습니다. 더 구체적인 이름을 시도해보세요.",
    "pl": "📍 Nie znaleziono miejsca. Spróbuj bardziej precyzyjnej nazwy.",
    "uk": "📍 Місце не знайдено. Спробуйте уточнити назву.",
    "nl": "📍 Locatie niet gevonden. Probeer een specifiekere naam.",
    "sv": "📍 Platsen hittades inte. Försök med ett mer specifikt namn.",
    "da": "📍 Stedet ikke fundet. Prøv et mere specifikt navn.",
    "fi": "📍 Paikkaa ei löydy. Kokeile tarkempaa nimeä.",
    "cs": "📍 Místo nenalezeno. Zkuste konkrétnější název.",
    "ro": "📍 Locul nu a fost găsit. Încercați un nume mai specific.",
    "hu": "📍 A hely nem található. Próbáljon pontosabb nevet.",
    "he": "📍 המיקום לא נמצא. נסה שם ספציפי יותר.",
    "vi": "📍 Không tìm thấy địa điểm. Thử tên cụ thể hơn.",
    "th": "📍 ไม่พบสถานที่ ลองใช้ชื่อที่เจาะจงกว่านี้",
    "id": "📍 Lokasi tidak ditemukan. Coba nama yang lebih spesifik.",
    "ms": "📍 Lokasi tidak dijumpai. Cuba nama yang lebih spesifik.",
    "ka": "📍 ადგილი ვერ მოიძებნა. სცადეთ უფრო კონკრეტული სახელი.",
    "hy": "📍 Վայրը չի գտնվել: Փորձեք ավելի կոնկրետ անուն:",
    "az": "📍 Yer tapılmadı. Daha konkret ad sınayın.",
    "kk": "📍 Орын табылмады. Нақтырақ атауды қолданып көріңіз.",
    "uz": "📍 Joy topilmadi. Aniqroq nom bilan sinab ko'ring.",
    "hi": "📍 स्थान नहीं मिला। अधिक विशिष्ट नाम आज़माएं।",
    "fa": "📍 مکان پیدا نشد. نام دقیق‌تری امتحان کنید.",
    "mn": "📍 Байршил олдсонгүй. Илүү тодорхой нэр ашиглана уу.",
}

# POI not-found messages
_POI_NOT_FOUND: dict[str, str] = {
    "en": "📍 No {category} found near {location}. Try a different area or category.",
    "ru": "📍 Рядом с {location} не найдено: {category}. Попробуйте другой район или категорию.",
    "de": "📍 Kein {category} in der Nähe von {location} gefunden.",
    "fr": "📍 Aucun {category} trouvé près de {location}.",
    "es": "📍 No se encontró {category} cerca de {location}.",
    "pt": "📍 Nenhum {category} encontrado perto de {location}.",
    "it": "📍 Nessun {category} trovato vicino a {location}.",
    "tr": "📍 {location} yakınında {category} bulunamadı.",
    "ar": "📍 لا يوجد {category} بالقرب من {location}.",
    "zh": "📍 在{location}附近未找到{category}。",
    "ja": "📍 {location}の近くに{category}が見つかりませんでした。",
    "ko": "📍 {location} 근처에서 {category}을(를) 찾을 수 없습니다.",
    "pl": "📍 Nie znaleziono {category} w pobliżu {location}.",
    "uk": "📍 Поряд з {location} не знайдено: {category}.",
    "ka": "📍 {location}-ის მახლობლად {category} ვერ მოიძებნა.",
    "hy": "📍 {location}-ի մոտ {category} չի գտնվել:",
}

# POI result format
_POI_RESULT: dict[str, str] = {
    "en": "📍 *{name}*\n{address}\nCoordinates: {lat}, {lon}",
    "ru": "📍 *{name}*\n{address}\nКоординаты: {lat}, {lon}",
    "de": "📍 *{name}*\n{address}\nKoordinaten: {lat}, {lon}",
    "fr": "📍 *{name}*\n{address}\nCoordonnées : {lat}, {lon}",
    "es": "📍 *{name}*\n{address}\nCoordenadas: {lat}, {lon}",
    "pt": "📍 *{name}*\n{address}\nCoordenadas: {lat}, {lon}",
    "it": "📍 *{name}*\n{address}\nCoordinate: {lat}, {lon}",
    "tr": "📍 *{name}*\n{address}\nKoordinatlar: {lat}, {lon}",
    "ar": "📍 *{name}*\n{address}\nالإحداثيات: {lat}, {lon}",
    "zh": "📍 *{name}*\n{address}\n坐标：{lat}, {lon}",
    "ja": "📍 *{name}*\n{address}\n座標：{lat}, {lon}",
    "ko": "📍 *{name}*\n{address}\n좌표: {lat}, {lon}",
    "pl": "📍 *{name}*\n{address}\nWspółrzędne: {lat}, {lon}",
    "uk": "📍 *{name}*\n{address}\nКоординати: {lat}, {lon}",
    "nl": "📍 *{name}*\n{address}\nCoördinaten: {lat}, {lon}",
    "sv": "📍 *{name}*\n{address}\nKoordinater: {lat}, {lon}",
    "da": "📍 *{name}*\n{address}\nKoordinater: {lat}, {lon}",
    "fi": "📍 *{name}*\n{address}\nKoordinaatit: {lat}, {lon}",
    "cs": "📍 *{name}*\n{address}\nSouřadnice: {lat}, {lon}",
    "ro": "📍 *{name}*\n{address}\nCoordonate: {lat}, {lon}",
    "hu": "📍 *{name}*\n{address}\nKoordináták: {lat}, {lon}",
    "he": "📍 *{name}*\n{address}\nקואורדינטות: {lat}, {lon}",
    "vi": "📍 *{name}*\n{address}\nTọa độ: {lat}, {lon}",
    "th": "📍 *{name}*\n{address}\nพิกัด: {lat}, {lon}",
    "id": "📍 *{name}*\n{address}\nKoordinat: {lat}, {lon}",
    "ms": "📍 *{name}*\n{address}\nKoordinat: {lat}, {lon}",
    "ka": "📍 *{name}*\n{address}\nკოორდინატები: {lat}, {lon}",
    "hy": "📍 *{name}*\n{address}\nՀամակարգային կոորդինատներ: {lat}, {lon}",
    "az": "📍 *{name}*\n{address}\nKoordinatlar: {lat}, {lon}",
    "kk": "📍 *{name}*\n{address}\nКоординаттар: {lat}, {lon}",
    "uz": "📍 *{name}*\n{address}\nKoordinatalar: {lat}, {lon}",
    "hi": "📍 *{name}*\n{address}\nनिर्देशांक: {lat}, {lon}",
    "fa": "📍 *{name}*\n{address}\nمختصات: {lat}, {lon}",
    "mn": "📍 *{name}*\n{address}\nКоординат: {lat}, {lon}",
    "sw": "📍 *{name}*\n{address}\nUratibu: {lat}, {lon}",
}


def _format_coord(template: str, name: str, lat: float, lon: float) -> str:
    return template.format(name=name, lat=f"{lat:.5f}", lon=f"{lon:.5f}")


# ─── SERVICE ──────────────────────────────────────────────────────────────────

class MapsService:
    """
    Mapbox API client.
    Geocoding and directions. Read-only. No state.
    """

    def __init__(self) -> None:
        self._token = settings.mapbox_token

    async def geocode(self, query: str, lang: str = "en") -> dict | None:
        """
        Forward geocoding: place name / address → coordinates + metadata.
        Returns first Mapbox feature or None.

        Validates query before sending to Mapbox:
          - rejects too-short / too-long strings
          - rejects rhetorical / complaint sentences that contain maps vocabulary
        """
        if not self._token:
            logger.warning("Mapbox token not set")
            return None

        if not _validate_query(query):
            return None

        params = {
            "access_token": self._token,
            "limit": 1,
            "language": _mb_lang(lang),
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/{query}.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                features = data.get("features", [])
                if not features:
                    logger.warning("Geocode: no results", extra={"query": query[:50]})
                    return None
                logger.info("Geocode success", extra={"query": query[:50]})
                return features[0]
        except Exception as exc:
            logger.error("MapsService.geocode failed", extra={
                "query": query[:50], "error": str(exc),
            })
            return None

    async def reverse_geocode(
        self,
        lon: float,
        lat: float,
        lang: str = "en",
    ) -> str | None:
        if not self._token:
            return None

        params = {
            "access_token": self._token,
            "limit": 1,
            "language": _mb_lang(lang),
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/{lon},{lat}.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                features = data.get("features", [])
                if not features:
                    return None
                return features[0].get("place_name")
        except Exception as exc:
            logger.error("MapsService.reverse_geocode failed", extra={
                "error": str(exc),
            })
            return None

    async def get_directions(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str = "driving",
        lang: str = "en",
    ) -> dict | None:
        if not self._token:
            return None

        coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        params = {
            "access_token": self._token,
            "geometries": "geojson",
            "language": _mb_lang(lang),
            "steps": "false",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_DIRECTIONS_URL}/{profile}/{coords}",
                    params=params,
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("MapsService.get_directions failed", extra={
                "error": str(exc),
            })
            return None

    def format_geocode(self, feature: dict, lang: str = "en") -> str:
        """Format geocode result into localised Telegram-ready string."""
        try:
            name   = feature.get("place_name", "Unknown")
            center = feature.get("center", [])

            if not center or len(center) < 2:
                return f"📍 {name}"

            lon, lat = center[0], center[1]
            template = _COORD_LABELS.get(lang) or _COORD_LABELS["en"]
            return _format_coord(template, name, lat, lon)

        except Exception as exc:
            logger.error("format_geocode failed", extra={"error": str(exc)})
            return "📍 Could not format location."

    def format_not_found(self, lang: str = "en") -> str:
        return _NOT_FOUND.get(lang) or _NOT_FOUND["en"]

    async def search_poi(
        self,
        category: str,
        location: str,
        lang: str = "en",
    ) -> dict | None:
        """
        POI search: find a place by category near a location.

        Strategy:
          1. Geocode the location string to get coordinates (lon, lat).
          2. Search Mapbox with the category query + proximity coordinates
             and types=poi to get the nearest matching place.

        Returns the first Mapbox feature or None.
        """
        if not self._token:
            logger.warning("Mapbox token not set")
            return None

        if not category:
            logger.warning("search_poi: empty category")
            return None

        params_base = {
            "access_token": self._token,
            "limit": 1,
            "language": _mb_lang(lang),
            "types": "poi",
        }

        # ── Step 1: resolve location to coordinates ───────────────────────────
        proximity: str | None = None
        if location:
            if not _validate_query(location):
                logger.warning("search_poi: invalid location string", extra={"location": location[:80]})
            else:
                try:
                    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                        response = await client.get(
                            f"{_BASE_URL}/{location}.json",
                            params={
                                "access_token": self._token,
                                "limit": 1,
                                "language": _mb_lang(lang),
                            },
                        )
                        response.raise_for_status()
                        data     = response.json()
                        features = data.get("features", [])
                        if features:
                            center   = features[0].get("center", [])
                            if len(center) >= 2:
                                proximity = f"{center[0]},{center[1]}"
                                logger.info(
                                    "search_poi: resolved location",
                                    extra={"location": location[:50], "proximity": proximity},
                                )
                except Exception as exc:
                    logger.warning(
                        "search_poi: failed to resolve location",
                        extra={"location": location[:50], "error": str(exc)},
                    )

        # ── Step 2: search for POI ────────────────────────────────────────────
        params = dict(params_base)
        if proximity:
            params["proximity"] = proximity

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/{category}.json",
                    params=params,
                )
                response.raise_for_status()
                data     = response.json()
                features = data.get("features", [])
                if not features:
                    logger.warning(
                        "search_poi: no results",
                        extra={"category": category, "location": location[:50]},
                    )
                    return None
                logger.info(
                    "search_poi: success",
                    extra={"category": category, "location": location[:50]},
                )
                return features[0]
        except Exception as exc:
            logger.error(
                "MapsService.search_poi failed",
                extra={"category": category, "error": str(exc)},
            )
            return None

    def format_poi(
        self,
        feature: dict,
        lang: str = "en",
    ) -> str:
        """Format POI search result into localised Telegram-ready string."""
        try:
            name    = feature.get("text", "") or feature.get("place_name", "Unknown")
            address = feature.get("place_name", "")
            center  = feature.get("center", [])

            if not center or len(center) < 2:
                return f"📍 *{name}*\n{address}"

            lon, lat = center[0], center[1]
            template = _POI_RESULT.get(lang) or _POI_RESULT["en"]
            return template.format(
                name=name,
                address=address,
                lat=f"{lat:.5f}",
                lon=f"{lon:.5f}",
            )
        except Exception as exc:
            logger.error("format_poi failed", extra={"error": str(exc)})
            return "📍 Could not format location."

    def format_poi_not_found(
        self,
        category: str,
        location: str,
        lang: str = "en",
    ) -> str:
        template = _POI_NOT_FOUND.get(lang) or _POI_NOT_FOUND["en"]
        return template.format(
            category=category or "place",
            location=location or "that area",
        )

    async def get_route(
        self,
        origin: str,
        destination: str,
        lang: str = "en",
    ) -> dict | None:
        """
        Geocode origin + destination, then get driving directions via Mapbox.

        Returns a dict with keys:
            origin_name, destination_name,
            distance_km, duration_min, steps (list of str)
        or None on any failure.
        """
        if not self._token:
            logger.warning("get_route: Mapbox token not set")
            return None

        # ── geocode both endpoints ────────────────────────────────────────────
        async def _geocode(place: str) -> tuple[float, float, str] | None:
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    r = await client.get(
                        f"{_BASE_URL}/{place}.json",
                        params={
                            "access_token": self._token,
                            "limit": 1,
                            "language": _mb_lang(lang),
                        },
                    )
                    r.raise_for_status()
                    features = r.json().get("features", [])
                    if not features:
                        return None
                    f = features[0]
                    lon, lat = f["center"]
                    name = f.get("place_name", place)
                    return lon, lat, name
            except Exception as exc:
                logger.error("get_route geocode failed", extra={"place": place, "error": str(exc)})
                return None

        origin_geo = await _geocode(origin)
        dest_geo   = await _geocode(destination)

        if not origin_geo or not dest_geo:
            logger.warning("get_route: geocoding failed", extra={
                "origin": origin, "destination": destination,
            })
            return None

        o_lon, o_lat, o_name = origin_geo
        d_lon, d_lat, d_name = dest_geo

        # ── get directions ────────────────────────────────────────────────────
        directions = await self.get_directions(
            origin=(o_lon, o_lat),
            destination=(d_lon, d_lat),
            profile="driving",
            lang=lang,
        )

        if not directions:
            return None

        try:
            route = directions["routes"][0]
            distance_km  = round(route["distance"] / 1000, 1)
            duration_min = round(route["duration"] / 60)
            return {
                "origin_name":      o_name,
                "destination_name": d_name,
                "distance_km":      distance_km,
                "duration_min":     duration_min,
            }
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("get_route: failed to parse directions", extra={"error": str(exc)})
            return None

    def format_route(self, route: dict, lang: str = "en") -> str:
        """Format route result into Telegram-ready string."""
        _TEMPLATES: dict[str, str] = {
            "en": "🗺 Route: {origin} → {destination}\n📏 Distance: {dist} km\n⏱ Drive time: ~{dur} min",
            "ru": "🗺 Маршрут: {origin} → {destination}\n📏 Расстояние: {dist} км\n⏱ Время в пути: ~{dur} мин",
            "de": "🗺 Route: {origin} → {destination}\n📏 Entfernung: {dist} km\n⏱ Fahrzeit: ~{dur} Min.",
            "fr": "🗺 Itinéraire: {origin} → {destination}\n📏 Distance: {dist} km\n⏱ Durée: ~{dur} min",
            "es": "🗺 Ruta: {origin} → {destination}\n📏 Distancia: {dist} km\n⏱ Tiempo: ~{dur} min",
            "tr": "🗺 Güzergah: {origin} → {destination}\n📏 Mesafe: {dist} km\n⏱ Süre: ~{dur} dak",
            "uk": "🗺 Маршрут: {origin} → {destination}\n📏 Відстань: {dist} км\n⏱ Час у дорозі: ~{dur} хв",
        }
        tpl = _TEMPLATES.get(lang) or _TEMPLATES["en"]
        return tpl.format(
            origin=route["origin_name"],
            destination=route["destination_name"],
            dist=route["distance_km"],
            dur=route["duration_min"],
        )

    def format_route_not_found(self, lang: str = "en") -> str:
        _MSGS: dict[str, str] = {
            "en": "🗺 Could not build a route. Check that both locations are correct.",
            "ru": "🗺 Не удалось построить маршрут. Уточните названия мест.",
            "de": "🗺 Route konnte nicht berechnet werden. Bitte Orte prüfen.",
            "fr": "🗺 Impossible de calculer l'itinéraire. Vérifiez les lieux.",
            "es": "🗺 No se pudo calcular la ruta. Comprueba los lugares.",
            "tr": "🗺 Güzergah oluşturulamadı. Lütfen yerleri kontrol edin.",
            "uk": "🗺 Не вдалося побудувати маршрут. Уточніть назви місць.",
        }
        return _MSGS.get(lang) or _MSGS["en"]


# Singleton
maps_service = MapsService()