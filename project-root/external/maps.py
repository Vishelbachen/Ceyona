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
            async with httpx.AsyncClient