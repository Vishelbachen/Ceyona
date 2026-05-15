from __future__ import annotations

import logging
import re

import httpx

from app.settings import settings
from i18n.t import t as _t

logger = logging.getLogger(__name__)


# ─── LANGUAGE MAP ─────────────────────────────────────────────────────────────
# Technical mapping: bot lang code → Mapbox language parameter.
# This belongs here, not in i18n, because it's an API concern.

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


# Mapbox "country" filter bias — restricts geocoding to most likely country
# for a given UI language. Prevents "центр" resolving to Centre, TX.
# Source: ISO 3166-1 alpha-2.
_LANG_COUNTRY_BIAS: dict[str, str] = {
    "ru": "ru",  "uk": "ua",  "be": "by",
    "kk": "kz",  "uz": "uz",  "az": "az",
    "ka": "ge",  "hy": "am",  "mn": "mn",
    "de": "de",  "fr": "fr",  "es": "es",
    "pt": "pt",  "it": "it",  "pl": "pl",
    "nl": "nl",  "sv": "se",  "da": "dk",
    "fi": "fi",  "cs": "cz",  "ro": "ro",
    "hu": "hu",  "tr": "tr",  "he": "il",
    "ar": "sa",  "fa": "ir",  "hi": "in",
    "zh": "cn",  "ja": "jp",  "ko": "kr",
    "vi": "vn",  "th": "th",  "id": "id",
    "ms": "my",
}


def _country_bias(lang: str) -> str | None:
    """Return ISO 3166-1 country code for Mapbox geocoding bias, or None."""
    return _LANG_COUNTRY_BIAS.get(lang)


# ─── QUERY VALIDATION ─────────────────────────────────────────────────────────

_QUERY_MIN_LEN  = 3
_QUERY_MAX_LEN  = 256

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

_QUERY_STOP_ONLY: frozenset[str] = frozenset({
    "here", "there", "this", "that", "it", "me", "my", "your",
    "тут", "там", "это", "моё", "мой", "моя", "твой", "твоя",
})


def _validate_query(query: str) -> bool:
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

    tokens = re.findall(r"\w+", lower)
    meaningful = [t for t in tokens if t not in _QUERY_STOP_ONLY and len(t) > 1]
    if not meaningful:
        logger.warning(
            "geocode: query rejected (only stop-words)",
            extra={"query": stripped[:80]},
        )
        return False

    return True


# ─── SERVICE ──────────────────────────────────────────────────────────────────

_BASE_URL       = "https://api.mapbox.com/geocoding/v5/mapbox.places"
_DIRECTIONS_URL = "https://api.mapbox.com/directions/v5/mapbox"
_TIMEOUT        = 10.0


class MapsService:
    """
    Mapbox API client.
    Geocoding, POI search and directions. Read-only. No state.
    All user-facing strings come from i18n/_t(); no language dicts here.
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
            return _t(
                "maps_coord_label", lang,
                name=name,
                lat=f"{lat:.5f}",
                lon=f"{lon:.5f}",
            )
        except Exception as exc:
            logger.error("format_geocode failed", extra={"error": str(exc)})
            return "📍 Could not format location."

    def format_not_found(self, lang: str = "en") -> str:
        return _t("maps_not_found", lang)

    async def search_poi(
        self,
        category: str,
        location: str,
        lang: str = "en",
    ) -> dict | None:
        """
        POI search: find a place by category near a location.

        Strategy:
          1. Geocode the location string to get coordinates (lon, lat).
          2. Search Mapbox with the category query + proximity coordinates
             and types=poi to get the nearest matching place.

        Returns the first Mapbox feature or None.
        """
        if not self._token:
            logger.warning("Mapbox token not set")
            return None

        if not category:
            logger.warning("search_poi: empty category")
            return None

        params_base = {
            "access_token": self._token,
            "limit": 5,
            "language": _mb_lang(lang),
            "types": "poi",
        }

        # ── Step 1: resolve location to coordinates ───────────────────────────
        proximity: str | None = None
        if location:
            if not _validate_query(location):
                logger.warning("search_poi: invalid location string", extra={"location": location[:80]})
            else:
                try:
                    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                        _loc_params: dict = {
                            "access_token": self._token,
                            "limit": 1,
                            "language": _mb_lang(lang),
                        }
                        _cb = _country_bias(lang)
                        if _cb:
                            _loc_params["country"] = _cb
                        response = await client.get(
                            f"{_BASE_URL}/{location}.json",
                            params=_loc_params,
                        )
                        response.raise_for_status()
                        data     = response.json()
                        features = data.get("features", [])
                        if features:
                            center   = features[0].get("center", [])
                            if len(center) >= 2:
                                proximity = f"{center[0]},{center[1]}"
                                logger.info(
                                    "search_poi: resolved location",
                                    extra={"location": location[:50], "proximity": proximity},
                                )
                except Exception as exc:
                    logger.warning(
                        "search_poi: failed to resolve location",
                        extra={"location": location[:50], "error": str(exc)},
                    )

        # ── Step 2: search for POI ────────────────────────────────────────────
        params = dict(params_base)
        if proximity:
            params["proximity"] = proximity

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.get(
                    f"{_BASE_URL}/{category}.json",
                    params=params,
                )
                response.raise_for_status()
                data     = response.json()
                features = data.get("features", [])
                if not features:
                    logger.warning(
                        "search_poi: no results",
                        extra={"category": category, "location": location[:50]},
                    )
                    return None
                logger.info(
                    "search_poi: success",
                    extra={"category": category, "location": location[:50], "count": len(features)},
                )
                return features  # list of up to 5 features
        except Exception as exc:
            logger.error(
                "MapsService.search_poi failed",
                extra={"category": category, "error": str(exc)},
            )
            return None

    def format_poi(
        self,
        features: list[dict] | dict,
        lang: str = "en",
    ) -> str:
        """Format POI search results (list or single) into a Telegram-ready string."""
        if isinstance(features, dict):
            features = [features]

        lines: list[str] = []
        for feature in features[:5]:
            try:
                name    = feature.get("text", "") or feature.get("place_name", "Unknown")
                address = feature.get("place_name", "")
                center  = feature.get("center", [])

                if not center or len(center) < 2:
                    lines.append(f"📍 *{name}*\n{address}")
                    continue

                lon, lat = center[0], center[1]
                lines.append(_t(
                    "maps_poi_result", lang,
                    name=name,
                    address=address,
                    lat=f"{lat:.5f}",
                    lon=f"{lon:.5f}",
                ))
            except Exception as exc:
                logger.error("format_poi failed for feature", extra={"error": str(exc)})
                continue

        return "\n\n".join(lines) if lines else "📍 Could not format location."

    def format_poi_not_found(
        self,
        category: str,
        location: str,
        lang: str = "en",
    ) -> str:
        return _t(
            "maps_poi_not_found", lang,
            category=category or "place",
            location=location or "that area",
        )

    async def get_route(
        self,
        origin: str,
        destination: str,
        lang: str = "en",
    ) -> dict | None:
        """
        Geocode origin + destination, then get driving directions via Mapbox.

        Returns a dict with keys:
            origin_name, destination_name,
            distance_km, duration_min
        or None on any failure.
        """
        if not self._token:
            logger.warning("get_route: Mapbox token not set")
            return None

        async def _geocode(place: str) -> tuple[float, float, str] | None:
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                    _params: dict = {
                        "access_token": self._token,
                        "limit": 1,
                        "language": _mb_lang(lang),
                    }
                    country = _country_bias(lang)
                    if country:
                        _params["country"] = country
                    r = await client.get(
                        f"{_BASE_URL}/{place}.json",
                        params=_params,
                    )
                    r.raise_for_status()
                    features = r.json().get("features", [])
                    if not features:
                        return None
                    f = features[0]
                    lon, lat = f["center"]
                    name = f.get("place_name", place)
                    return lon, lat, name
            except Exception as exc:
                logger.error("get_route geocode failed", extra={"place": place, "error": str(exc)})
                return None

        origin_geo = await _geocode(origin)
        dest_geo   = await _geocode(destination)

        if not origin_geo or not dest_geo:
            logger.warning("get_route: geocoding failed", extra={
                "origin": origin, "destination": destination,
            })
            return None

        o_lon, o_lat, o_name = origin_geo
        d_lon, d_lat, d_name = dest_geo

        directions = await self.get_directions(
            origin=(o_lon, o_lat),
            destination=(d_lon, d_lat),
            profile="driving",
            lang=lang,
        )

        if not directions:
            return None

        try:
            route = directions["routes"][0]
            distance_km  = round(route["distance"] / 1000, 1)
            duration_min = round(route["duration"] / 60)
            return {
                "origin_name":      o_name,
                "destination_name": d_name,
                "distance_km":      distance_km,
                "duration_min":     duration_min,
            }
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("get_route: failed to parse directions", extra={"error": str(exc)})
            return None

    def format_route(self, route: dict, lang: str = "en") -> str:
        """Format route result into Telegram-ready localised string."""
        dist = route["distance_km"]
        dur  = route["duration_min"]

        # Guard: Mapbox returns 0.0/0 when geocoding produced identical or
        # invalid coordinates (e.g. "центр" without a city name resolved to
        # the wrong place, then both origin and destination hit the same coords).
        # In this case the route data is meaningless — return not-found instead.
        if dist == 0.0 and dur == 0:
            logger.warning(
                "format_route: zero route (bad geocode?)",
                extra={
                    "origin":      route.get("origin_name", ""),
                    "destination": route.get("destination_name", ""),
                },
            )
            return self.format_route_not_found(lang)

        return _t(
            "maps_route_result", lang,
            origin=route["origin_name"],
            destination=route["destination_name"],
            dist=str(dist),
            dur=str(dur),
        )

    def format_route_not_found(self, lang: str = "en") -> str:
        return _t("maps_route_not_found", lang)


# Singleton
maps_service = MapsService()