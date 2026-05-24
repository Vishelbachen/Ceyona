import asyncio
import logging
from contextlib import asynccontextmanager

from app.bootstrap import bootstrap, shutdown
from fastapi import FastAPI, Request
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

    # ── media group aggregator ────────────────────────────
    from transport.telegram.media_group_aggregator import MediaGroupAggregator
    from transport.telegram.vision_handler import handle_vision_group

    aggregator: MediaGroupAggregator = state["media_group_aggregator"]

    async def _on_group_ready(group_id: str, items) -> None:
        """
        Called by the aggregator once all photos in an album have arrived.
        Runs the full vision + pipeline path and sends the result to the user.
        """
        from transport.telegram.webhook import _send_message

        # Derive user context from first item's message_id via Supabase is not
        # feasible here without chat_id, so we store it alongside items.
        # The chat_id is encoded as a prefix in group_id: "{chat_id}:{tg_group_id}"
        try:
            chat_id_str, _ = group_id.split(":", 1)
            chat_id = int(chat_id_str)
        except (ValueError, AttributeError):
            logger.error("MediaGroup: cannot parse chat_id from group_id", extra={"group_id": group_id})
            return

        caption = next((i.caption for i in items if i.caption), "")
        file_ids = [i.file_id for i in items]

        try:
            vision_result = await handle_vision_group(
                file_ids=file_ids,
                caption=caption,
                lang="en",   # TODO: persist lang in aggregator item
            )
        except Exception as exc:
            logger.error("MediaGroup vision group failed", extra={"error": str(exc)})
            await _send_message(chat_id, "❌ Could not process the images.")
            return

        await _send_message(chat_id, vision_result.text or "❌ Could not process the images.")

    aggregator._on_group_ready = _on_group_ready
    app.state.media_group_aggregator = aggregator

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


@app.get("/debug")
async def debug() -> dict:
    """
    Live functional checks for every external integration.

    Unlike /providers (key presence only), /debug actually calls each service
    and reports the real error when something fails.

    Checks:
      - compound-mini  : complete_with_tools() with a trivial prompt
      - compound       : complete_with_tools() with a trivial prompt
      - search         : Tavily → SerpAPI → SearXNG with a known query
      - weather        : OpenWeatherMap for "London"
      - maps/geocode   : Mapbox geocode for "Red Square, Moscow"
      - maps/route     : Mapbox route from Moscow to Saint Petersburg
      - embedding      : HuggingFace BGE-large embed of a short string
      - groq/llm       : plain complete() with llama-3.1-8b-instant
    """
    import time
    import traceback

    from external.maps import maps_service
    from external.search import search_service
    from external.weather import weather_service
    from llm.groq_client import groq_client
    from llm.model_router import DEEP_AGENT_MODEL, FAST_AGENT_MODEL

    results: dict[str, dict] = {}

    # ── helper ────────────────────────────────────────────────────────────────
    def _ok(detail: str = "") -> dict:
        return {"status": "ok", "detail": detail}

    def _err(exc: Exception) -> dict:
        return {
            "status": "error",
            "error": str(exc),
            "type": type(exc).__name__,
            "trace": traceback.format_exc(limit=5),
        }

    # ── groq plain LLM ────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        resp = await groq_client.complete(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=10,
            temperature=0.0,
        )
        results["groq_llm"] = _ok(f"{resp.text.strip()!r} in {time.monotonic()-t0:.2f}s")
    except Exception as exc:
        results["groq_llm"] = _err(exc)

    # ── compound-mini ─────────────────────────────────────────────────────────
    _PING_TOOLS = [{
        "type": "function",
        "function": {
            "name": "ping",
            "description": "Test tool — always call this immediately.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }]
    try:
        t0 = time.monotonic()
        resp = await groq_client.complete_with_tools(
            model=FAST_AGENT_MODEL,
            messages=[{"role": "user", "content": "Call the ping tool now."}],
            tools=_PING_TOOLS,
            max_tokens=64,
            temperature=0.0,
        )
        detail = f"finish_type={type(resp).__name__} in {time.monotonic()-t0:.2f}s"
        results["compound_mini"] = _ok(detail)
    except Exception as exc:
        results["compound_mini"] = _err(exc)

    # ── compound (deep) ───────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        resp = await groq_client.complete_with_tools(
            model=DEEP_AGENT_MODEL,
            messages=[{"role": "user", "content": "Call the ping tool now."}],
            tools=_PING_TOOLS,
            max_tokens=64,
            temperature=0.0,
        )
        detail = f"finish_type={type(resp).__name__} in {time.monotonic()-t0:.2f}s"
        results["compound_deep"] = _ok(detail)
    except Exception as exc:
        results["compound_deep"] = _err(exc)

    # ── web search ────────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        hits = await search_service.search(query="current date", lang="en", num=3)
        detail = f"{len(hits)} results in {time.monotonic()-t0:.2f}s"
        if hits:
            detail += f" | first: {hits[0].get('title', '')[:60]}"
        results["search"] = _ok(detail) if hits else {
            "status": "warning",
            "detail": "all providers returned 0 results",
        }
    except Exception as exc:
        results["search"] = _err(exc)

    # ── weather ───────────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        data = await weather_service.get_current(city="London", lang="en")
        if data:
            temp = data.get("main", {}).get("temp", "?")
            desc = data.get("weather", [{}])[0].get("description", "?")
            results["weather"] = _ok(f"London: {temp}°C, {desc} in {time.monotonic()-t0:.2f}s")
        else:
            results["weather"] = {"status": "error", "error": "get_current returned None"}
    except Exception as exc:
        results["weather"] = _err(exc)

    # ── maps geocode ──────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        feature = await maps_service.geocode(query="Red Square, Moscow", lang="en")
        if feature:
            coords = feature.get("geometry", {}).get("coordinates", "?")
            results["maps_geocode"] = _ok(f"coords={coords} in {time.monotonic()-t0:.2f}s")
        else:
            results["maps_geocode"] = {"status": "error", "error": "geocode returned None"}
    except Exception as exc:
        results["maps_geocode"] = _err(exc)

    # ── maps route ────────────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        route = await maps_service.get_route(
            origin="Moscow, Russia",
            destination="Saint Petersburg, Russia",
            lang="en",
        )
        if route:
            results["maps_route"] = _ok(f"route ok in {time.monotonic()-t0:.2f}s")
        else:
            results["maps_route"] = {"status": "error", "error": "get_route returned None"}
    except Exception as exc:
        results["maps_route"] = _err(exc)

    # ── HuggingFace embedding ─────────────────────────────────────────────────
    try:
        from llm.hf_client import BGE_LARGE, hf_client
        t0 = time.monotonic()
        vecs = await hf_client.embed(["test embedding ping"], model=BGE_LARGE)
        if vecs and vecs[0]:
            results["embedding"] = _ok(f"dim={len(vecs[0])} in {time.monotonic()-t0:.2f}s")
        else:
            results["embedding"] = {"status": "error", "error": "embed returned empty vector"}
    except Exception as exc:
        results["embedding"] = _err(exc)

    # ── summary ───────────────────────────────────────────────────────────────
    ok_count  = sum(1 for v in results.values() if v.get("status") == "ok")
    err_count = sum(1 for v in results.values() if v.get("status") == "error")
    results["_summary"] = {
        "ok": ok_count,
        "error": err_count,
        "warning": len(results) - 1 - ok_count - err_count,
    }

    return results