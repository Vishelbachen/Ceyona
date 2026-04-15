import requests
import logging

logger = logging.getLogger(__name__)


class MapsService:
    def __init__(self, settings):
        self.google_key = settings.GOOGLE_MAPS_API_KEY
        self.mapbox_key = settings.MAPBOX_TOKEN

    # -------------------------
    # GOOGLE GEOCODING
    # -------------------------
    def geocode_google(self, address: str) -> dict:
        if not address:
            return {"error": "empty_address"}

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"

            params = {
                "address": address,
                "key": self.google_key
            }

            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            if not data.get("results"):
                return {"error": "not_found"}

            loc = data["results"][0]["geometry"]["location"]

            return {
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "formatted": data["results"][0].get("formatted_address")
            }

        except Exception as e:
            logger.warning(f"[GOOGLE MAPS FAIL] {e}")
            return {"error": "google_failed"}

    # -------------------------
    # MAPBOX GEOCODING
    # -------------------------
    def geocode_mapbox(self, address: str) -> dict:
        if not address:
            return {"error": "empty_address"}

        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"

            params = {
                "access_token": self.mapbox_key
            }

            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()

            if not data.get("features"):
                return {"error": "not_found"}

            coords = data["features"][0]["center"]

            return {
                "lng": coords[0],
                "lat": coords[1],
                "formatted": data["features"][0].get("place_name")
            }

        except Exception as e:
            logger.warning(f"[MAPBOX FAIL] {e}")
            return {"error": "mapbox_failed"}

    # -------------------------
    # SMART FALLBACK ROUTER
    # -------------------------
    def geocode(self, address: str) -> dict:
        try:
            result = self.geocode_google(address)

            if result and "error" not in result:
                return result

        except Exception:
            pass

        return self.geocode_mapbox(address)