import logging

from app.settings import settings

logger = logging.getLogger(__name__)


async def bootstrap() -> dict:
    from events.event_bus import event_bus
    from events.event_dispatcher import setup_dispatcher
    from events.event_store import EventStore
    from redis.asyncio import from_url as redis_from_url
    from supabase import create_client

    # ─── Redis ──────────────────────────────────────────
    # socket_timeout=None: pubsub.listen() blocks indefinitely waiting for
    # the next keyspace event — that's normal idle, not a hang. The default
    # ~10s socket_timeout was killing MediaGroupAggregator's listener on any
    # quiet period (redis.exceptions.TimeoutError: Timeout reading from ...).
    # health_check_interval keeps the connection alive across Upstash's
    # managed-proxy idle disconnects.
    redis = redis_from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=None,
        socket_connect_timeout=10,
        socket_keepalive=True,
        health_check_interval=30,
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

    # ─── MediaGroup aggregator ──────────────────────────────────────────────
    # Wires the Redis-backed album aggregator.  The on_group_ready callback
    # is intentionally left as a no-op here; webhook.py overrides it via
    # app.state.media_group_aggregator after the app is created so it can
    # access send_message helpers in the same module.
    from transport.telegram.media_group_aggregator import MediaGroupAggregator

    async def _media_group_noop(group_id: str, items) -> None:  # noqa: E731
        logger.warning(
            "MediaGroupAggregator: on_group_ready not wired — override in app setup",
            extra={"group_id": group_id, "count": len(items)},
        )

    media_group_aggregator = MediaGroupAggregator(redis, _media_group_noop)
    await media_group_aggregator.start()
    logger.info("MediaGroupAggregator started")

    return {
        "redis": redis,
        "supabase": supabase,
        "settings": settings,
        "event_store": store,
        "media_group_aggregator": media_group_aggregator,
    }


async def shutdown(state: dict) -> None:
    aggregator = state.get("media_group_aggregator")
    if aggregator:
        await aggregator.stop()
    redis = state.get("redis")
    if redis:
        await redis.aclose()