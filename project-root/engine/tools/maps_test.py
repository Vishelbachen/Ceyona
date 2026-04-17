import os
import httpx


class MapsTest:
    def __init__(self):
        self.key = os.getenv("GOOGLE_MAPS_API_KEY")

    async def test_geocode(self, address: str = "Tbilisi") -> dict:
        if not self.key:
            return {"ok": False, "error": "NO_API_KEY_IN_ENV"}

        url = "https://maps.googleapis.com/maps/api/geocode/json"

        params = {
            "address": address,
            "key": self.key
        }

        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params)

        try:
            data = r.json()
        except Exception:
            return {"ok": False, "error": "INVALID_JSON_RESPONSE"}

        return {
            "ok": data.get("status") == "OK",
            "status": data.get("status"),
            "error_message": data.get("error_message"),
            "raw": data
        }