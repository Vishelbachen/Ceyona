import logging
import httpx
from app.settings import settings

logger = logging.getLogger(__name__)
_BASE = "https://api.mapbox.com/geocoding/v5/mapbox.places"
_TIMEOUT = 10.0


async def geocode(query: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(
                f"{_BASE}/{query}.json",
                params={"access_token": settings.mapbox_token, "limit": 1},
            )
            r.raise_for_status()
            features = r.json().get("features", [])
            if not features:
                return {}
            f = features[0]
            return {
                "place_name": f.get("place_name"),
                "longitude": f["geometry"]["coordinates"][0],
                "latitude": f["geometry"]["coordinates"][1],
            }
    except Exception as exc:
        logger.error("Geocode failed", extra={"query": query, "error": str(exc)})
        return {}