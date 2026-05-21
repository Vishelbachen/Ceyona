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
    from llm.hf_client import hf_client
    app.state.hf_client = hf_client

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


@app.get("/metrics")
async def metrics() -> dict:
    """
    Observability snapshot endpoint.

    Returns in-memory counters and gauges accumulated since process start.
    Data is per-process and resets on restart — no persistence by design.
    See architecture.md §7 / audit §7.3 / §10.1.
    """
    from observability.metrics import snapshot
    return snapshot()


@app.get("/models")
async def models():
    from llm.groq_client import groq_client

    models = await groq_client._client.models.list()

    ids = sorted(m.id for m in models.data)

    return {
        "count": len(ids),
        "available_models": ids,
    }


@app.get("/providers")
async def providers(request: Request):
    from app.settings import settings
    from llm.groq_client import groq_client

    status = {}

    # ── Redis ───────────────────────────────────────────
    try:
        await request.app.state.redis.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"

    # ── Supabase ────────────────────────────────────────
    try:
        # Supabase Python client is synchronous — must run in thread to avoid blocking event loop
        await asyncio.to_thread(
            lambda: request.app.state.supabase.table("user_balances").select("user_id").limit(1).execute()
        )
        status["supabase"] = "ok"
    except Exception:
        status["supabase"] = "error"

    # ── Groq ────────────────────────────────────────────
    try:
        await groq_client._client.models.list()
        status["groq"] = "ok"
    except Exception:
        status["groq"] = "error"

    # ── HuggingFace ─────────────────────────────────────
    try:
        if settings.hf_token:
            status["huggingface"] = "ok"
        else:
            status["huggingface"] = "missing"
    except Exception:
        status["huggingface"] = "error"

    # ── Telegram ────────────────────────────────────────
    try:
        if settings.bot_token:
            status["telegram"] = "ok"
        else:
            status["telegram"] = "missing"
    except Exception:
        status["telegram"] = "error"

    # ── Brevo ───────────────────────────────────────────
    try:
        if settings.brevo_api_key:
            status["brevo"] = "ok"
        else:
            status["brevo"] = "missing"
    except Exception:
        status["brevo"] = "error"

    # ── Encryption ──────────────────────────────────────
    try:
        if settings.encryption_key:
            status["encryption"] = "ok"
        else:
            status["encryption"] = "missing"
    except Exception:
        status["encryption"] = "error"

    # ── JWT ─────────────────────────────────────────────
    try:
        if settings.jwt_secret:
            status["jwt"] = "ok"
        else:
            status["jwt"] = "missing"
    except Exception:
        status["jwt"] = "error"

    # ── Mapbox ──────────────────────────────────────────
    try:
        if settings.mapbox_token:
            status["mapbox"] = "ok"
        else:
            status["mapbox"] = "missing"
    except Exception:
        status["mapbox"] = "error"

    # ── OpenWeather ─────────────────────────────────────
    try:
        if settings.openweather_api_key:
            status["openweather"] = "ok"
        else:
            status["openweather"] = "missing"
    except Exception:
        status["openweather"] = "error"

    # ── SerpAPI ─────────────────────────────────────────
    try:
        if settings.serpapi_key:
            status["serpapi"] = "ok"
        else:
            status["serpapi"] = "missing"
    except Exception:
        status["serpapi"] = "error"

    # ── Tavily ──────────────────────────────────────────
    try:
        if settings.tavily_api_key:
            status["tavily"] = "ok"
        else:
            status["tavily"] = "missing"
    except Exception:
        status["tavily"] = "error"

    # ── SearXNG ─────────────────────────────────────────
    try:
        if settings.searxng_url:
            status["searxng"] = "ok"
        else:
            status["searxng"] = "missing"
    except Exception:
        status["searxng"] = "error"

    # ── Sentry ──────────────────────────────────────────
    try:
        if settings.sentry_dsn:
            status["sentry"] = "ok"
        else:
            status["sentry"] = "missing"
    except Exception:
        status["sentry"] = "error"

    # ── TON Wallet ──────────────────────────────────────
    try:
        if settings.ton_wallet:
            status["ton_wallet"] = "ok"
        else:
            status["ton_wallet"] = "missing"
    except Exception:
        status["ton_wallet"] = "error"

    # ── Webhook ─────────────────────────────────────────
    try:
        if settings.webhook_url:
            status["webhook"] = "ok"
        else:
            status["webhook"] = "missing"
    except Exception:
        status["webhook"] = "error"

    # ── Allowed Origins ─────────────────────────────────
    try:
        if settings.allowed_origins:
            status["cors"] = "ok"
        else:
            status["cors"] = "missing"
    except Exception:
        status["cors"] = "error"

    # ── Raw env presence checks ─────────────────────────
    status["BOT_TOKEN"] = "ok" if settings.bot_token else "missing"
    status["BREVO_API_KEY"] = "ok" if settings.brevo_api_key else "missing"
    status["ENCRYPTION_KEY"] = "ok" if settings.encryption_key else "missing"
    status["GROQ_API_KEY"] = "ok" if settings.groq_api_key else "missing"
    status["JWT_SECRET"] = "ok" if settings.jwt_secret else "missing"
    status["MAPBOX_TOKEN"] = "ok" if settings.mapbox_token else "missing"
    status["OPENWEATHER_API_KEY"] = "ok" if settings.openweather_api_key else "missing"
    status["REDIS_URL"] = "ok" if settings.redis_url else "missing"
    status["SENTRY_DSN"] = "ok" if settings.sentry_dsn else "missing"
    status["SERPAPI_KEY"] = "ok" if settings.serpapi_key else "missing"
    status["TAVILY_API_KEY"] = "ok" if settings.tavily_api_key else "missing"
    status["SEARXNG_URL"] = "ok" if settings.searxng_url else "missing"
    status["SUPABASE_ANON_KEY"] = "ok" if settings.supabase_anon_key else "missing"
    status["SUPABASE_SERVICE_ROLE_KEY"] = "ok" if settings.supabase_service_role_key else "missing"
    status["SUPABASE_URL"] = "ok" if settings.supabase_url else "missing"
    status["TON_WALLET"] = "ok" if settings.ton_wallet else "missing"
    status["WEBHOOK_URL"] = "ok" if settings.webhook_url else "missing"
    status["HF_TOKEN"] = "ok" if settings.hf_token else "missing"
    status["ALLOWED_ORIGINS"] = "ok" if settings.allowed_origins else "missing"

    return status