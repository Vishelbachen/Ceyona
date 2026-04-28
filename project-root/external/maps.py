from typing import Any, Dict, List, Optional


class MapsClient:
    """
    AI Platform v4.7 — Maps External Client

    RESPONSIBILITY:
    - Geocoding (address ↔ coordinates)
    - Route calculation
    - Location lookup via external map provider

    STRICT RULES:
    - No routing decisions for user intent
    - No ranking of places
    - No business logic
    - No LLM / retrieval / memory usage
    - No UI formatting
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.mapbox.com"

    async def geocode(self, address: str) -> Dict[str, Any]:
        """
        Converts address → coordinates (raw response).
        """

        return {
            "address": address,
            "lat": 0.0,
            "lng": 0.0,
            "source": "mock_mapbox",
        }

    async def reverse_geocode(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Converts coordinates → address (raw response).
        """

        return {
            "lat": lat,
            "lng": lng,
            "address": "mock address",
            "source": "mock_mapbox",
        }

    async def get_route(
        self,
        origin: str,
        destination: str,
        mode: str = "driving",
    ) -> Dict[str, Any]:
        """
        Returns raw route data between two points.
        """

        return {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "distance_km": 0,
            "duration_min": 0,
            "steps": [],
            "source": "mock_mapbox",
        }

    async def search_places(
        self,
        query: str,
        proximity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Basic place search (raw results only).
        """

        return [
            {
                "name": query,
                "lat": 0.0,
                "lng": 0.0,
                "category": "unknown",
            }
        ]