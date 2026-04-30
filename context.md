# Текущая архитектура, все файлы готовы и помечены ×, но желательно их добить и/или переписать/улучшить в случае и по мере необходимости 


# Архитектура v4.7


app/
├── main.py ×
├── bootstrap.py ×
├── settings.py ×

transport/telegram/
├── webhook.py ×
├── update_handler.py ×
├── message_router.py ×
├── callback_handler.py ×
└── auth_middleware.py ×

core/kernel/
├── execution_policy_kernel.py ×
├── decision_matrix.py ×
├── cost_model.py ×
├── policy_registry.py ×
core/execution/
└── orchestrator.py ×

events/
├── event_bus.py ×
├── event_store.py ×
├── event_types.py ×
├── event_dispatcher.py ×
└── event_replay.py ×

cognition/
├── intent_engine.py × 
├── reasoning_engine.py ×
├── multi_agent_coordinator.py ×
└── response_synthesizer.py ×

agents/
├── fast_agent.py ×
├── deep_agent.py ×
├── creative_agent.py ×
├── safety_agent.py ×
└── consensus_engine.py ×

payments/
├── ton_client.py ×
├── pricing_engine.py ×
├── access_controller.py ×
├── usage_meter.py ×
└── wallet_manager.py ×

memory/
├── supabase_store.py  ×
├── vector_memory.py ×
└── conversation_history.py ×

llm/
├── groq_client.py ×
├── hf_client.py ×
├── model_router.py ×
├── prompt_engine.py ×
└── fallback_handler.py ×

external/
├── weather.py ×
├── maps.py ×
├── search.py ×
└── web_tools.py ×

notifications/
├── email_service.py ×
└── event_notifier.py ×

security/
├── auth.py ×
├── encryption.py ×
├── rate_limiter.py ×
└── origin_guard.py ×

observability/
├── logger.py ×
├── metrics.py ×
├── tracing.py ×
└── sentry.py ×  

infra/
├── config_loader.py ×
├── env_validator.py ×
└── healthcheck.py ×

retrieval/
├── retrieval_engine.py ×
├── retrieval_models.py ×
└── query_preprocessor.py ×

retrieval/dense/
├── bge_engine.py ×
retrieval/fusion/
├── hybrid_scorer.py ×
retrieval/reranker/
├── cross_encoder.py ×
retrieval/sparse/
└── bm25_engine.py ×
retrieval/cache/
├── embedding_cache.py ×
├── query_cache.py ×
├── rerank_cache.py ×
└── ttl_policy.py ×

context/
├── assembler.py ×
├── context_models.py ×
└── serializer.py ×

contracts/
├── retrieval_contracts.py ×
├── context_contracts.py ×
└── shared_types.py ×


# Все файлы текущей архитектуры с кодом в порядке структуры 


# app/main.py

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.bootstrap import bootstrap, shutdown
from infra.env_validator import validate
from observability.logger import setup_logging
from observability.sentry import init_sentry

logger = logging.getLogger(__name__)


async def _wallet_poll_loop(supabase) -> None:
    """
    Background task: poll TON wallet every 60 seconds.
    Runs for the lifetime of the app.
    """
    from payments.wallet_manager import WalletManager
    manager = WalletManager(supabase)

    while True:
        try:
            count = await manager.process_incoming()
            if count:
                logger.info("TON payments processed", extra={"count": count})
        except Exception as exc:
            logger.error("Wallet poll error", extra={"error": str(exc)})
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    validate()
    init_sentry()

    state = await bootstrap()
    app.state.redis = state["redis"]
    app.state.supabase = state["supabase"]
    app.state.settings = state["settings"]

    # ── rate limiter ──────────────────────────────────────
    from security.rate_limiter import init_rate_limiter
    init_rate_limiter(state["redis"])

    # ── webhook registration ──────────────────────────────
    from transport.telegram.webhook import register_webhook
    await register_webhook()

    # ── background wallet poller ──────────────────────────
    wallet_task = asyncio.create_task(
        _wallet_poll_loop(state["supabase"]),
        name="wallet_poller",
    )

    yield

    # ── graceful shutdown ─────────────────────────────────
    wallet_task.cancel()
    try:
        await wallet_task
    except asyncio.CancelledError:
        logger.info("Wallet poller stopped")

    await shutdown(state)


app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

from transport.telegram.webhook import router as telegram_router  # noqa: E402
app.include_router(telegram_router)


@app.get("/health")
async def health(request: Request):
    from infra.healthcheck import full_health
    return await full_health(request.app.state.redis, request.app.state.supabase)



# app/bootstrap.py

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

