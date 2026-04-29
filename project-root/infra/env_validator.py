import logging
import sys

logger = logging.getLogger(__name__)

_REQUIRED = [
    "BOT_TOKEN",
    "JWT_SECRET",
    "ENCRYPTION_KEY",
    "WEBHOOK_URL",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "REDIS_URL",
]


def validate_env() -> None:
    """
    Check all required env vars are present.
    Exits with code 1 if any are missing.
    Call before app startup.
    """
    import os
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        logger.critical("Missing required env vars", extra={"missing": missing})
        sys.exit(1)
    logger.info("Env validation passed")