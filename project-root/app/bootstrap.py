import logging

from app.settings import settings

logger = logging.getLogger(__name__)


async def bootstrap() -> dict:
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

    event_store = EventStore(redis)
    setup_dispatcher(event_bus, event_store)
    logger.info("EventDispatcher registered")

    # ─── Payments ───────────────────────────────────────
    from payments.access_controller import AccessController
    from payments.usage_meter import UsageMeter

    access_controller = AccessController(supabase)
    usage_meter = UsageMeter(supabase)

    return {
        "redis": redis,
        "supabase": supabase,
        "settings": settings,
        "event_store": event_store,
        "access_controller": access_controller,
        "usage_meter": usage_meter,
    }


async def shutdown(state: dict) -> None:
    redis = state.get("redis")
    if redis:
        await redis.aclose()

    from payments.ton_client import ton_client
    await ton_client.aclose()

    from llm.hf_client import hf_client
    await hf_client.aclose()

    logger.info("Shutdown complete")