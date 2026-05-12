import logging

from app.settings import settings

logger = logging.getLogger(__name__)


async def bootstrap() -> dict:
    from redis.asyncio import from_url as redis_from_url
    from supabase import create_client
    from events.event_bus import event_bus
    from events.event_store import EventStore
    from events.event_dispatcher import setup_dispatcher

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

    # ─── Event system ───────────────────────────────────
    store = EventStore(redis)
    setup_dispatcher(event_bus, store)
    logger.info("EventDispatcher ready")

    # ─── Intent examples seed ───────────────────────────────────────────────
    # Runs only if table is empty. No-op on subsequent starts.
    try:
        from cognition.intent_examples import seed_intent_examples
        from llm.hf_client import hf_client
        seeded = await seed_intent_examples(supabase, hf_client)
        if seeded:
            logger.info("intent_examples seeded", extra={"count": seeded})
    except Exception as exc:
        logger.error("intent_examples seed failed — classify will use fallback", extra={"error": str(exc)})

    return {
        "redis": redis,
        "supabase": supabase,
        "settings": settings,
        "event_store": store,
    }


async def shutdown(state: dict) -> None:
    redis = state.get("redis")
    if redis:
        await redis.aclose()