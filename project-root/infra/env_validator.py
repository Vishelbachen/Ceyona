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
    "supabase_anon_key",
    "supabase_service_role_key",
]


def validate() -> bool:
    missing = []
    for key in _REQUIRED:
        val = getattr(settings, key, "")
        if not val:
            missing.append(key)

    if missing:
        logger.error("Missing required env vars", extra={"missing": missing})
        return False

    logger.info("Env validation passed")
    return True