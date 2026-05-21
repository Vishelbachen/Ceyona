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
    "mapbox_token",  # required: geocoding, maps
    # Search providers: at least one of tavily_api_key / serpapi_key should be set,
    # but neither is hard-required here — missing both degrades search gracefully.
]


def validate() -> None:
    missing = [k for k in _REQUIRED if not getattr(settings, k, "")]
    if missing:
        logger.critical("Missing required env vars", extra={"missing": missing})
        sys.exit(1)
    logger.info("Env validation passed")