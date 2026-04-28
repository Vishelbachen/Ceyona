from app.settings import settings


async def bootstrap() -> dict:
    """
    Initialise all infrastructure clients and return them
    as a plain dict (the app state). Called once on startup.
    """
    from redis.asyncio import from_url as redis_from_url
    from supabase import create_client

    # ─── Redis ──────────────────────────────────────────
    redis = redis_from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # ─── Supabase ───────────────────────────────────────
    supabase = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )

    return {
        "redis": redis,
        "supabase": supabase,
        "settings": settings,
    }


async def shutdown(state: dict) -> None:
    """
    Graceful teardown of all infrastructure clients.
    Called once on shutdown.
    """
    redis = state.get("redis")
    if redis:
        await redis.aclose()