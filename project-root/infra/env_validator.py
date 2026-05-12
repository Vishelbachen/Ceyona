import sys
import logging

from app.settings import settings

logger = logging.getLogger(__name__)

_REQUIRED = [
    "bot_token",
    "jwt_secret",
    "encryption_key",
    "webhook_url",
    "groq_api_key",
    "hf_token",
    "supabase_url",
    "supabase_service_role_key",
    "redis_url",
    "serpapi_key",   # required: search, maps_poi, hotel/place queries
    "mapbox_token",  # required: geocoding, maps
]


def validate() -> None:
    missing = [k for k in _REQUIRED if not getattr(settings, k, "")]
    if missing:
        logger.critical("Missing required env vars", extra={"missing": missing})
        sys.exit(1)
    logger.info("Env validation passed")
