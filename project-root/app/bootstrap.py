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

    # ─── Event System ───────────────────────────────────
    from events.event_bus import event_bus
    from events.event_store import EventStore
    from events.event_dispatcher import setup_dispatcher

    event_store = EventStore(redis=redis)
    setup_dispatcher(bus=event_bus, store=event_store)

    return {
        "redis":       redis,
        "supabase":    supabase,
        "event_bus":   event_bus,
        "event_store": event_store,
        "settings":    settings,
    }


async def shutdown(state: dict) -> None:
    """
    Graceful teardown of all infrastructure clients.
    Called once on shutdown.
    """
    redis = state.get("redis")
    if redis:
        await redis.aclose()