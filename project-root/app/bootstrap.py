import logging

from app.settings import settings

logger = logging.getLogger(__name__)


async def bootstrap() -> dict:
    from events.event_bus import event_bus
    from events.event_dispatcher import setup_dispatcher
    from events.event_store import EventStore
    from infra.supabase_client import ResilientSupabase
    from redis.asyncio import from_url as redis_from_url

    # ─── Redis ──────────────────────────────────────────
    # TWO separate clients, not one shared connection:
    #
    # `redis` — used for every regular command (GET/SETEX/pipeline/zrevrange/
    # Lua scripts): EventStore, rate_limiter, EmbeddingCache/QueryCache/
    # RerankCache, MediaGroupAggregator's add()/flush(). Has a finite
    # socket_timeout so a hung/managed-proxy connection (Upstash) fails fast
    # instead of hanging the whole webhook request forever.
    #
    # `redis_pubsub` — used ONLY by MediaGroupAggregator's keyspace listener
    # (pubsub.listen()). It legitimately blocks indefinitely waiting for the
    # next event, which is normal idle, not a hang — hence socket_timeout=None.
    #
    # Previously both roles shared ONE client with socket_timeout=None. That
    # was set to fix the listener (redis.exceptions.TimeoutError: Timeout
    # reading from ...), but it silently disabled the timeout on every OTHER
    # operation too — including EventStore/rate_limiter/caches. A stalled
    # Upstash connection on any of those would hang the request indefinitely
    # rather than timing out after 10s as intended.
    redis = redis_from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=10,
        socket_keepalive=True,
        health_check_interval=30,
    )
    redis_pubsub = redis_from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=None,
        socket_connect_timeout=10,
        socket_keepalive=True,
        health_check_interval=30,
    )

    # ─── Supabase ───────────────────────────────────────
    supabase = ResilientSupabase(
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

    media_group_aggregator = MediaGroupAggregator(redis, _media_group_noop, redis_pubsub=redis_pubsub)
    await media_group_aggregator.start()
    logger.info("MediaGroupAggregator started")

    return {
        "redis": redis,
        "redis_pubsub": redis_pubsub,
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
    redis_pubsub = state.get("redis_pubsub")
    if redis_pubsub:
        await redis_pubsub.aclose()