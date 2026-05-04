from __future__ import annotations

import logging
import re

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

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


# Singleton
maps_service = MapsService()