import requests


class MapsService:
    def __init__(self, settings):
        self.google_key = settings.GOOGLE_MAPS_API_KEY
        self.mapbox_key = settings.MAPBOX_TOKEN

    # -------------------------
    # GEOCODING (Google)
    # -------------------------
    def geocode_google(self, address: str) -> dict:
        url = "https://maps.googleapis.com/maps/api/geocode/json"

        params = {
            "address": address,
            "key": self.google_key
        }

        res = requests.get(url, params=params).json()

        if not res["results"]:
            return {"error": "not_found"}

        loc = res["results"][0]["geometry"]["location"]

        return {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "formatted": res["results"][0]["formatted_address"]
        }

    # -------------------------
    # GEOCODING (Mapbox fallback)
    # -------------------------
    def geocode_mapbox(self, address: str) -> dict:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"

        params = {
            "access_token": self.mapbox_key
        }

        res = requests.get(url, params=params).json()

        if not res["features"]:
            return {"error": "not_found"}

        coords = res["features"][0]["center"]

        return {
            "lng": coords[0],
            "lat": coords[1],
            "formatted": res["features"][0]["place_name"]
        }

    # -------------------------
    # AUTO SELECTOR
    # -------------------------
    def geocode(self, address: str) -> dict:
        try:
            return self.geocode_google(address)
        except Exception:
            return self.geocode_mapbox(address)