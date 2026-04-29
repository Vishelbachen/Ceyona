import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"
_TIMEOUT = 10.0


class MapsService:
    """
    Mapbox API client.
    Geocoding and directions. Read-only. No state.
    """

    def __init__(self) -> None:
        self._token = settings.mapbox_token

    async def geocode(self, query: str, lang: str = "en") -> dict | None:
        """
        Forward geocoding: place name → coordinates.
        Returns first result or None.
        """
        if not self._token:
            logger.warning("Mapbox token not set")
            return None

        # Mapbox uses language codes like 'en', 'ru', 'de', etc.
        params = {
            "access_token": self._token,
            "limit": 1,
            "language": lang,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                url = f"{_BASE_URL}/{query}.json"
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                features = data.get("features", [])
                if not features:
                    return None
                return features[0]
        except Exception as exc:
            logger.error("MapsService.geocode failed", extra={
                "query": query,
                "error": str(exc),
            })
            return None

    async def reverse_geocode(
        self,
        lon: float,
        lat: float,
        lang: str = "en",
    ) -> str | None:
        """
        Reverse geocoding: coordinates → place name string.
        """
        if not self._token:
            return None

        params = {
            "access_token": self._token,
            "limit": 1,
            "language": lang,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                url = f"{_BASE_URL}/{lon},{lat}.json"
                response = await client.get(url, params=params)
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
        """
        Get driving/walking directions between two coordinate pairs.
        profile: "driving" | "walking" | "cycling"
        Returns raw Mapbox directions response or None.
        """
        if not self._token:
            return None

        coords = f"{origin[0]},{origin[1]};{destination[0]},{destination[1]}"
        params = {
            "access_token": self._token,
            "geometries": "geojson",
            "language": lang,
            "steps": "false",
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                url = f"{_DIRECTIONS_URL}/{profile}/{coords}"
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error("MapsService.get_directions failed", extra={
                "error": str(exc),
            })
            return None

    def format_geocode(self, feature: dict, lang: str = "en") -> str:
        """Format geocode result into human-readable string."""
        name = feature.get("place_name", "")
        coords = feature.get("center", [])
        if coords and len(coords) >= 2:
            lon, lat = coords[0], coords[1]

            _labels: dict[str, str] = {
                "en": f"📍 *{name}*\nCoordinates: {lat:.4f}, {lon:.4f}",
                "ru": f"📍 *{name}*\nКоординаты: {lat:.4f}, {lon:.4f}",
                "de": f"📍 *{name}*\nKoordinaten: {lat:.4f}, {lon:.4f}",
                "fr": f"📍 *{name}*\nCoordonnées : {lat:.4f}, {lon:.4f}",
                "es": f"📍 *{name}*\nCoordenadas: {lat:.4f}, {lon:.4f}",
                "zh": f"📍 *{name}*\n坐标：{lat:.4f}, {lon:.4f}",
                "ar": f"📍 *{name}*\nالإحداثيات: {lat:.4f}, {lon:.4f}",
            }
            return _labels.get(lang) or _labels["en"]

        return f"📍 {name}"


# Singleton
maps_service = MapsService()