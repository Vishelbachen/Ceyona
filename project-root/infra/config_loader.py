from app.settings import settings


def get_config() -> dict:
    """Return sanitized config snapshot (no secrets)."""
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "webhook_url": settings.webhook_url,
        "redis_url": settings.redis_url,
        "supabase_url": settings.supabase_url,
    }