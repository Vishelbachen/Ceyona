from __future__ import annotations

import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL       = "https://api.mapbox.com/geocoding/v5/mapbox.places"
_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"
_TIMEOUT        = 10.0

# Mapbox supported language codes
_MB_LANG_MAP: dict[str, str] = {
    "en": "en", "ru": "ru", "de": "de", "fr": "fr",
    "es": "es", "pt": "pt", "it": "it", "tr": "tr",
    "ar": "ar", "zh": "zh", "ja": "ja", "ko": "ko",
    "pl": "pl", "uk": "uk", "nl": "nl", "sv": "sv",
    "da": "da", "fi": "fi", "cs": "cs", "ro": "ro",
    "hu": "hu", "he": "he", "vi": "vi", "th": "th",
    "id": "id", "ms": "ms",
}

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
    "ka": "📍 *{name}*\nკოორდინატები: {lat}, {lon}",
    "hy": "📍 *{name}*\nՀամակարգային: {lat}, {lon}",
}

_NOT_FOUND: dict[str, str] = {
    "en": "📍 Location not found. Try a more specific name.",
    "ru": "📍 Место не найдено. Попробуйте уточнить название.",
    "de": "📍 Ort nicht gefunden. Versuche einen genaueren Namen.",
    "fr": "📍 Lieu introuvable. Essayez un nom plus précis.",
    "es": "📍 Lugar no encontrado. Intenta con un nombre más específico.",
    "ka": "📍 ადგილი ვერ მოიძებნა. სცადეთ უფრო კონკრეტული სახელი.",
}


def _mb_lang(lang: str) -> str:
    return _MB_LANG_MAP.get(lang, "en")


def _format_coord(label_template: str, name: str, lat: float, lon: float) -> str:
    return label_template.format(
        name=name,
        lat=f"{lat:.5f}",
        lon=f"{lon:.5f}",
    )


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
        """
        if not self._token:
            logger.warning("Mapbox token not set")
            return None

        params = {
            "access_token": self._token,
            "limit": 1,
            "language": _mb_lang(lang),
        }

        try:
            # URL-encode the query manually — httpx handles it
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                url = f"{_BASE_URL}/{httpx.URL(query)}.json"
                response = await client.get(
                    f"{_BASE_URL}/{query}.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                features = data.get("features", [])
                if not features:
                    logger.warning("Geocode: no results", extra={"query": query})
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