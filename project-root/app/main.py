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
        await asyncio.sleep(10)


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
        Routes through the full vision + orchestrator pipeline — same path
        as a single photo, but using handle_vision_group for batch extraction.
        """
        from payments.access_controller import AccessController
        from transport.telegram.message_router import UpdateType
        from transport.telegram.update_handler import handle_message
        from transport.telegram.webhook import _send_message

        # chat_id is encoded as a prefix in group_id: "{chat_id}:{tg_group_id}"
        try:
            chat_id_str, _ = group_id.split(":", 1)
            chat_id = int(chat_id_str)
        except (ValueError, AttributeError):
            logger.error("MediaGroup: cannot parse chat_id from group_id", extra={"group_id": group_id})
            return

        caption = next((i.caption for i in items if i.caption), "")
        file_ids = [i.file_id for i in items]
        user_id = chat_id  # for Telegram bots: chat_id == user_id for private chats

        # Resolve lang: prefer item that has a caption (user typed something),
        # fall back to first item, then "ru" as last resort.
        item_with_caption = next((i for i in items if i.caption), None)
        lang = (
            item_with_caption.lang
            if item_with_caption
            else (items[0].lang if items else "ru")
        )

        # Fetch user balance
        user_balance = 0.0
        try:
            ac = AccessController(state["supabase"])
            balance_result = await ac.get_balance(user_id)
            user_balance = balance_result.balance_usd
        except Exception as exc:
            logger.error("MediaGroup: balance fetch failed", extra={"error": str(exc)})

        # Run full vision pipeline via handle_vision_group + orchestrator
        try:
            vision_result = await handle_vision_group(
                file_ids=file_ids,
                caption=caption,
                lang=lang,
            )
        except Exception as exc:
            logger.error("MediaGroup vision group failed", extra={"error": str(exc)})
            await _send_message(chat_id, "❌ Could not process the images.")
            return

        # If vision extraction failed entirely — do not feed err_text into the
        # pipeline. The LLM would hallucinate on "Содержимое изображений: ошибка".
        # Send a localized error message directly instead.
        if vision_result.failed:
            from i18n.t import get_system_message
            await _send_message(chat_id, get_system_message("vision_error", lang))
            return

        # Always run the full pipeline for albums — vision extraction is context
        # Build the user_message that the pipeline LLM will receive.
        #
        # Structure matters: without an explicit task the model has no instruction
        # and falls back to generic reasoning ("Вопрос не имеет отношения...").
        # Three parts are required:
        #   1. Context  — how many images, user's own words if any
        #   2. Task     — explicit instruction derived from caption or default
        #   3. Content  — extraction output from handle_vision_group
        #
        # When the user provided a caption (e.g. "решите задачу", "что здесь?")
        # that IS the task — use it verbatim.
        # When there is no caption the default task is to describe the images.
        _context_line = (
            f"Пользователь прислал альбом из {len(file_ids)} изображений"
            + (f' с подписью: "{caption.strip()}"' if caption.strip() else "")
            + "."
        )
        _task_line = (
            f"Задача пользователя: {caption.strip()}"
            if caption.strip()
            else "Задача: опиши что на изображениях."
        )
        _annotated_vision = (
            f"{_context_line}\n\n"
            f"{_task_line}\n\n"
            f"Содержимое изображений:\n{vision_result.text}"
        )
        synthetic_update = {"_voice_transcript": _annotated_vision}
        try:
            result = await handle_message(
                update=synthetic_update,
                update_type=UpdateType.MESSAGE,
                user_id=user_id,
                user_balance=user_balance,
                lang=lang,
                supabase=state["supabase"],
                redis=state["redis"],
                hf_client=app.state.hf_client,
                request_id=f"mediagroup:{group_id}",
                app_state=app.state,
                input_type="image_group",
                vision_intent=vision_result.intent_result,
                # is_vision routing guard: album always carries extracted image
                # descriptions as user_message — never a raw user query.
                # Prevents CHAIN_OF_THOUGHT on ANALYSIS/INSTRUCTION intents.
                # needs_pipeline=True path only (false path returns directly).
                is_vision=True,
            )
            if result.denied:
                from i18n.t import get_system_message
                await _send_message(chat_id, get_system_message("no_response", "ru"))
                return
            if result.text:
                await _send_message(chat_id, result.text)
        except Exception as exc:
            logger.error("MediaGroup orchestrator failed", extra={"error": str(exc)})
            # Fallback: send raw vision extraction
            fallback_text = vision_result.text or "❌ Could not process the images."
            await _send_message(chat_id, fallback_text)

    aggregator._on_group_ready = _on_group_ready
    app.state.media_group_aggregator = aggregator

    # ── rate limiter ──────────────────────────────────────
    from security.rate_limiter import init_rate_limiter
    init_rate_limiter(state["redis"])

    # ── webhook registration ──────────────────────────────
    # Non-fatal: Telegram already knows the webhook URL from the previous run.
    # A transient timeout (e.g. Worker not yet warm, HF→CF network blip) must
    # not kill the whole process — incoming updates will keep arriving anyway.
    from transport.telegram.webhook import register_webhook
    try:
        ok = await register_webhook()
        if not ok:
            logger.warning("Webhook registration returned ok=False — will retry on next restart")
    except Exception as exc:
        logger.warning("Webhook registration failed — app continues", extra={"error": str(exc)})

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


@app.get("/")
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
    """
    Full model availability check across all 20 models used by Ceyona.

    Splits into two provider groups:
      - groq: 17 models verified against live Groq models.list() API
      - hf:   3 HuggingFace models (BGE embeddings + reranker) pinged via embed_raw()

    Each model entry:
      - available: bool  — whether the model ID appears in Groq's list (or HF responds)
      - role: str        — what this model does in the system

    Top-level "all_ok" is False if any required model is unavailable.
    """
    import asyncio
    from llm.groq_client import groq_client
    from llm.hf_client import BGE_LARGE, BGE_SMALL, BGE_RERANKER, hf_client

    # ── Groq: fetch live model list ───────────────────────────────────────────
    groq_list = await groq_client._client.models.list()
    groq_ids = {m.id for m in groq_list.data}

    def _groq(model_id: str, role: str) -> dict:
        return {"available": model_id in groq_ids, "role": role, "model": model_id}

    groq_models = {
        # ── LLM tier primaries ──────────────────────────────────────────
        "fast_primary":        _groq("openai/gpt-oss-20b",           "LLM · Tier.FAST primary (1000 TPS)"),
        "general_primary":     _groq("qwen/qwen3.6-27b",             "LLM · Tier.GENERAL primary + vision + multilingual"),
        "heavy_primary":       _groq("openai/gpt-oss-120b",          "LLM · Tier.HEAVY primary + consensus arbiter"),
        # ── Agent layer ─────────────────────────────────────────────────
        "fast_agent":          _groq("groq/compound-mini",           "Agent · FAST path synthesizer (web search, 1 tool)"),
        "deep_agent":          _groq("groq/compound",                "Agent · GENERAL path synthesizer (web search, 10 tools)"),
        # ── Safety gate ─────────────────────────────────────────────────
        "safety_pass1":        _groq("meta-llama/llama-prompt-guard-2-22m", "Safety · Pass1 fast rejection (22M BERT, $0.03/1M)"),
        "safety_pass2_86m":    _groq("meta-llama/llama-prompt-guard-2-86m", "Safety · Pass2 deep classifier (86M BERT, $0.04/1M)"),
        "safety_safeguard":    _groq("openai/gpt-oss-safeguard-20b", "Safety · Pass2 enforcement ($0.075/$0.30 per 1M)"),
        # ── Speech ──────────────────────────────────────────────────────
        "whisper_primary":     _groq("whisper-large-v3",             "ASR · High-quality transcription ($0.111/hr)"),
        "whisper_turbo":       _groq("whisper-large-v3-turbo",       "ASR · Fast transcription, default ($0.040/hr)"),
        "tts_english":         _groq("canopylabs/orpheus-v1-english", "TTS · English voice synthesis ($22/1M chars)"),
        "tts_arabic":          _groq("canopylabs/orpheus-arabic-saudi", "TTS · Arabic voice synthesis ($40/1M chars)"),
        # ── Multilingual ────────────────────────────────────────────────
        "multilingual_arabic": _groq("allam-2-7b",                   "Multilingual · Arabic normalization (allam, FAST rates)"),
        # ── Utility ─────────────────────────────────────────────────────
        "shaper":              _groq("openai/gpt-oss-20b",           "Utility · heavy_input_shaper (same as fast_primary)"),
        "long_context":        _groq("qwen/qwen3.6-27b",             "Utility · long-context transformer (same as general_primary)"),
    }

    # ── HuggingFace: ping each model with a minimal embed call ───────────────
    async def _hf_ping(model_id: str) -> bool:
        try:
            vecs = await hf_client.embed_raw(["ping"], model=model_id)
            return bool(vecs and vecs[0])
        except Exception:
            return False

    bge_large_ok, bge_small_ok, bge_reranker_ok = await asyncio.gather(
        _hf_ping(BGE_LARGE),
        _hf_ping(BGE_SMALL),
        _hf_ping(BGE_RERANKER),
    )

    hf_models = {
        "bge_large":   {"available": bge_large_ok,   "role": "Embedding · primary ($0.10/1M tokens, HF serverless)",  "model": BGE_LARGE},
        "bge_small":   {"available": bge_small_ok,   "role": "Embedding · fast fallback ($0.02/1M tokens, HF serverless)", "model": BGE_SMALL},
        "bge_reranker":{"available": bge_reranker_ok,"role": "Reranking · cross-encoder ($0.10/1M token-pairs, HF serverless)", "model": BGE_RERANKER},
    }

    all_groq_ok = all(v["available"] for v in groq_models.values())
    all_hf_ok   = all(v["available"] for v in hf_models.values())

    return {
        "all_ok": all_groq_ok and all_hf_ok,
        "groq": {
            "all_ok": all_groq_ok,
            "total_in_registry": len(groq_ids),
            "models": groq_models,
        },
        "hf": {
            "all_ok": all_hf_ok,
            "models": hf_models,
        },
    }


@app.get("/routing")
async def routing():
    """
    Current model routing table — which model handles each role.

    Reads directly from model_router constants (source of truth).
    No live API calls — instant response, safe to poll frequently.
    Use /models to verify each model is actually available on Groq/HF.
    """
    from llm.model_router import (
        FAST_AGENT_MODEL, DEEP_AGENT_MODEL, CONSENSUS_MODEL,
        SHAPER_MODEL, LONG_CONTEXT_MODEL,
        MULTILINGUAL_ARABIC_MODEL, MULTILINGUAL_OTHER_MODEL,
        SAFETY_PASS1_MODEL, SAFETY_PASS2_MODELS,
        WHISPER_PRIMARY, WHISPER_FAST,
        ORPHEUS_ENGLISH, ORPHEUS_ARABIC,
    )
    from llm.hf_client import BGE_LARGE, BGE_SMALL, BGE_RERANKER

    return {
        "llm": {
            "fast":    "openai/gpt-oss-20b",
            "general": "qwen/qwen3.6-27b",
            "heavy":   "openai/gpt-oss-120b",
        },
        "agents": {
            "fast":  FAST_AGENT_MODEL,
            "deep":  DEEP_AGENT_MODEL,
            "consensus": CONSENSUS_MODEL,
        },
        "safety": {
            "pass1":  SAFETY_PASS1_MODEL,
            "pass2":  SAFETY_PASS2_MODELS,
        },
        "speech": {
            "asr_primary": WHISPER_PRIMARY,
            "asr_fast":    WHISPER_FAST,
            "tts_english": ORPHEUS_ENGLISH,
            "tts_arabic":  ORPHEUS_ARABIC,
        },
        "multilingual": {
            "arabic": MULTILINGUAL_ARABIC_MODEL,
            "other":  MULTILINGUAL_OTHER_MODEL,
        },
        "utility": {
            "shaper":        SHAPER_MODEL,
            "long_context":  LONG_CONTEXT_MODEL,
        },
        "hf": {
            "embedding_primary":  BGE_LARGE,
            "embedding_fallback": BGE_SMALL,
            "reranker":           BGE_RERANKER,
        },
    }



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
      - groq/llm       : plain complete() with openai/gpt-oss-20b
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
            model="openai/gpt-oss-20b",
            reasoning_effort="low",
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=10,
            temperature=0.0,
        )
        results["groq_llm"] = _ok(f"{resp.text.strip()!r} in {time.monotonic()-t0:.2f}s")
    except Exception as exc:
        results["groq_llm"] = _err(exc)

    # ── compound-mini ─────────────────────────────────────────────────────────
    # NOTE: compound models do NOT accept custom tool schemas (architecture.md §40,
    # audit §13.1) — passing tools= always raises HTTP 400. Production code
    # (agents/compound_agent.py) calls complete() without tools; mirror that here.
    try:
        t0 = time.monotonic()
        resp = await groq_client.complete(
            model=FAST_AGENT_MODEL,
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=64,
            temperature=0.0,
        )
        detail = f"{resp.text.strip()!r} in {time.monotonic()-t0:.2f}s"
        results["compound_mini"] = _ok(detail)
    except Exception as exc:
        results["compound_mini"] = _err(exc)

    # ── compound (deep) ───────────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        resp = await groq_client.complete(
            model=DEEP_AGENT_MODEL,
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=64,
            temperature=0.0,
        )
        detail = f"{resp.text.strip()!r} in {time.monotonic()-t0:.2f}s"
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
        vecs = await hf_client.embed_raw(["test embedding ping"], model=BGE_LARGE)
        if vecs and vecs[0]:
            results["embedding"] = _ok(f"dim={len(vecs[0])} in {time.monotonic()-t0:.2f}s")
        else:
            results["embedding"] = {"status": "error", "error": "embed returned empty vector (no exception raised)"}
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