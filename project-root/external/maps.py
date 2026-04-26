from __future__ import annotations

import aiohttp
from typing import Dict, Any, Optional

from infra.config_loader import get_settings


settings = get_settings()


# =========================
# MAPS CLIENT
# =========================
class MapsClient:
    """
    ROLE:
    - fetch raw geolocation / map data from Mapbox
    - return normalized but NON-interpreted results

    STRICT RULES:
    - no routing logic
    - no distance reasoning
    - no place ranking
    - no UI formatting
    """

    BASE_URL = "https://api.mapbox.com"

    def __init__(self):
        self.token = settings.MAPBOX_TOKEN

    # =========================
    # GEOCODING (ADDRESS → COORDS)
    # =========================
    async def geocode(self, query: str) -> Dict[str, Any]:

        url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{query}.json"

        params = {
            "access_token": self.token,
            "limit": 5,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()

        return self._normalize_geocode(data)

    # =========================
    # REVERSE GEOCODING (COORDS → ADDRESS)
    # =========================
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> Dict[str, Any]:

        url = f"{self.BASE_URL}/geocoding/v5/mapbox.places/{longitude},{latitude}.json"

        params = {
            "access_token": self.token,
            "limit": 5,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()

        return self._normalize_geocode(data)

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize_geocode(self, data: Dict[str, Any]) -> Dict[str, Any]:

        features = data.get("features", [])

        return {
            "results": [
                {
                    "name": f.get("text"),
                    "full_name": f.get("place_name"),
                    "coordinates": f.get("center"),
                    "type": f.get("place_type"),
                }
                for f in features
            ],
            "raw": data,
        }