import asyncio
import logging
from contextlib import asynccontextmanager

from app.bootstrap import bootstrap, shutdown
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from infra.env_validator import validate
from observability.logger import setup_logging
from observability.sentry import init_sentry
from security.auth import verify_token

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

    # ARCH-change 2026-07: outgoing Telegram messages go through Supabase's
    # `outbox` table instead of a direct HF → Worker HTTP call (see
    # transport/telegram/webhook.py::_post_via_worker for why). Wire the
    # module-level handle it needs, once, here.
    from transport.telegram.webhook import set_outbox_supabase
    set_outbox_supabase(app.state.supabase)

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
        # Worker's per-photo Storage ref, now carried through MediaGroupItem
        # (see media_group_aggregator.py) — keyed by file_id so
        # handle_vision_group can look one up per image. Items whose Worker
        # download/upload failed simply have attachment_ref=None and fall
        # back to a per-image Telegram re-download inside handle_vision_group.
        attachment_refs = {i.file_id: i.attachment_ref for i in items if i.attachment_ref}
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
                supabase=state["supabase"],
                attachment_refs=attachment_refs,
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
        logger.warning("Webhook registration failed — app continues", extra={"error": repr(exc) or type(exc).__name__})

    # ── background wallet poller ──────────────────────────
    wallet_task = asyncio.create_task(
        _wallet_poll_loop(state["supabase"]),
        name="wallet_poller",
    )

    # ── background queue consumer (Telegram updates from pending_updates) ──
    # См. transport/telegram/queue_consumer.py — заменяет прежний
    # синхронный forward Cloudflare Worker → HF на push-queue архитектуру.
    from transport.telegram.queue_consumer import queue_consumer_loop
    queue_task = asyncio.create_task(
        queue_consumer_loop(app.state),
        name="telegram_queue_consumer",
    )

    yield

    # ── graceful shutdown ─────────────────────────────────
    wallet_task.cancel()
    queue_task.cancel()
    try:
        await wallet_task
    except asyncio.CancelledError:
        logger.info("Wallet poller stopped")
    try:
        await queue_task
    except asyncio.CancelledError:
        logger.info("Telegram queue consumer stopped")

    await shutdown(state)


app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# origin_guard.py owns the allowed-origins logic.
# For the Telegram bot, allowed_origins defaults to '*' — Telegram servers are
# not browsers, CORS does not apply to webhook calls. This middleware exists
# for future web clients hitting the admin/diagnostic endpoints.
from app.settings import settings as _settings  # noqa: E402

_origins = [o.strip() for o in _settings.allowed_origins.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── JWT dependency for admin routes ───────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """
    FastAPI dependency: validate Bearer JWT for administrative endpoints.
    Usage: add `_: int = Depends(require_admin)` to any admin route.

    Protected: /metrics, /models, /providers, /routing, /debug
    NOT protected: /health (monitoring must stay open), /webhook (Telegram)
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    return user_id


from transport.telegram.webhook import router as telegram_router  # noqa: E402

app.include_router(telegram_router)


@app.get("/")
@app.get("/health")
async def health(request: Request):
    from infra.healthcheck import full_health
    return await full_health(request.app.state.redis, request.app.state.supabase)


@app.get("/metrics")
async def metrics(_: int = Depends(require_admin)) -> dict:
    """
    Observability snapshot endpoint.

    Returns in-memory counters and gauges accumulated since process start.
    Data is per-process and resets on restart — no persistence by design.
    See architecture.md §7 / audit §7.3 / §10.1.
    """
    from observability.metrics import snapshot
    return snapshot()


@app.get("/models")
async def models(_: int = Depends(require_admin)):
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
    from llm.hf_client import BGE_LARGE, BGE_RERANKER, BGE_SMALL, hf_client

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
async def routing(_: int = Depends(require_admin)):
    """
    Current model routing table — which model handles each role.

    Reads directly from model_router constants (source of truth).
    No live API calls — instant response, safe to poll frequently.
    Use /models to verify each model is actually available on Groq/HF.
    """
    from llm.hf_client import BGE_LARGE, BGE_RERANKER, BGE_SMALL
    from llm.model_router import (
        CONSENSUS_MODEL,
        DEEP_AGENT_MODEL,
        FAST_AGENT_MODEL,
        LONG_CONTEXT_MODEL,
        MULTILINGUAL_ARABIC_MODEL,
        MULTILINGUAL_OTHER_MODEL,
        ORPHEUS_ARABIC,
        ORPHEUS_ENGLISH,
        SAFETY_PASS1_MODEL,
        SAFETY_PASS2_MODELS,
        SHAPER_MODEL,
        WHISPER_FAST,
        WHISPER_PRIMARY,
    )

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



@app.get("/providers")
async def providers(request: Request, _: int = Depends(require_admin)):
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
async def debug(_: int = Depends(require_admin)) -> dict:
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


# ─── TEMPORARY: attachment-layer empirical tests (2026-07) ────────────────────
# Purpose: answer three open questions from the Attachment/signed-URL design
# (see infra/attachment.py, app/settings.py flags groq_whisper_accepts_ogg_opus,
# groq_vision_accepts_signed_url, groq_whisper_accepts_signed_url) against the
# REAL Groq API, using the most recently stored voice/photo in Supabase
# Storage — not synthetic data. Test 4 was added afterward to close a gap
# noticed once speech_to_text.py's transcribe() was made to use a single
# request-shape pattern (pure files=, no data=) for both its URL and bytes
# paths — test 1 had only confirmed the bytes path with files=+data= mixed,
# so test 4 verifies the pure-files= bytes shape actually used in code now.
#
# DELETE THIS ROUTE once the three flags have been confirmed/settled. It exists
# only to be reachable from a phone browser (no terminal/curl available), so
# it uses a URL query secret (?key=...) instead of the Bearer-JWT admin auth
# used by /debug — a phone browser can't attach an Authorization header to a
# plain link tap. Reuses settings.webhook_secret as that shared secret purely
# for convenience (it's already a secret only you and the Worker know); it has
# no other relationship to Telegram webhook verification.
@app.get("/debug/attachment-tests")
async def attachment_tests(request: Request, key: str = "") -> dict:
    import time
    import traceback

    import httpx
    from app.settings import settings

    if not settings.webhook_secret or key != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="bad or missing ?key=")

    supabase = request.app.state.supabase
    results: dict[str, dict] = {}

    def _ok(detail: str = "") -> dict:
        return {"status": "ok", "detail": detail}

    def _err(exc: Exception) -> dict:
        return {"status": "error", "error": str(exc), "type": type(exc).__name__,
                "trace": traceback.format_exc(limit=3)}

    def _find_latest(kind: str) -> str | None:
        """Return the path of the most recently modified object under {kind}/ in the bucket."""
        try:
            entries = supabase.storage.from_(settings.attachment_bucket).list(kind)
        except Exception:
            return None
        if not entries:
            return None
        entries = sorted(entries, key=lambda e: e.get("updated_at", e.get("created_at", "")), reverse=True)
        return f"{kind}/{entries[0]['name']}"

    # ── locate latest voice + photo ───────────────────────────────────────────
    voice_path = _find_latest("voice")
    photo_path = _find_latest("photo")
    results["_found"] = {"voice_path": voice_path, "photo_path": photo_path}

    if not voice_path and not photo_path:
        results["_summary"] = {"note": "no voice/photo found in bucket — send the bot one of each first"}
        return results

    async def _signed_url(path: str) -> str:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: supabase.storage.from_(settings.attachment_bucket).create_signed_url(path, 300)
        )
        url = result.get("signedURL") or result.get("signedUrl") or result.get("signed_url")
        if url.startswith("/"):
            url = f"{settings.supabase_url.rstrip('/')}{url}"
        return url

    # ── TEST 1: groq_whisper_accepts_ogg_opus — raw bytes, no WAV conversion ──
    # NOTE (2026-07, first run): this failed with "file must be one of the
    # following types: [flac mp3 mp4 mpeg mpga m4a ogg opus wav webm]" — not
    # because the OGG/Opus codec was rejected, but because Groq determines
    # the type from the filename EXTENSION in the multipart part, and
    # Telegram voice messages are stored in this bucket with a ".oga"
    # extension (see voice_path), which isn't in Groq's accepted list even
    # though ".ogg" is. Forcing the multipart filename's extension to
    # ".ogg" below (content unchanged — .oga and .ogg are the same OGG
    # container, Telegram just uses the .oga spelling) isolates the actual
    # question: does Groq accept the OGG/Opus bytes Telegram produces.
    if voice_path:
        try:
            t0 = time.monotonic()
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(
                None, lambda: supabase.storage.from_(settings.attachment_bucket).download(voice_path)
            )
            _forced_name = voice_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] + ".ogg"
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    files={"file": (_forced_name, raw, "audio/ogg")},
                    data={"model": "whisper-large-v3"},
                )
            if r.status_code == 200:
                text = r.json().get("text", "")
                results["test1_whisper_ogg_direct"] = _ok(
                    f"200 in {time.monotonic()-t0:.2f}s, renamed {voice_path.rsplit('/', 1)[-1]!r}→{_forced_name!r}, transcript={text[:120]!r}"
                )
            else:
                results["test1_whisper_ogg_direct"] = {
                    "status": "error", "http_status": r.status_code, "body": r.text[:300],
                    "note": f"renamed {voice_path.rsplit('/', 1)[-1]!r}→{_forced_name!r} to isolate codec vs. filename-extension issue",
                }
        except Exception as exc:
            results["test1_whisper_ogg_direct"] = _err(exc)
    else:
        results["test1_whisper_ogg_direct"] = {"status": "skipped", "reason": "no voice file found"}

    # ── TEST 2: groq_vision_accepts_signed_url ────────────────────────────────
    if photo_path:
        try:
            t0 = time.monotonic()
            url = await _signed_url(photo_path)
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}",
                             "Content-Type": "application/json"},
                    json={
                        "model": "qwen/qwen3.6-27b",
                        "reasoning_effort": "none",
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": url}},
                            {"type": "text", "text": "Describe this image in one sentence."},
                        ]}],
                    },
                )
            if r.status_code == 200:
                desc = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                results["test2_vision_signed_url"] = _ok(
                    f"200 in {time.monotonic()-t0:.2f}s, description={desc[:150]!r}"
                )
            else:
                results["test2_vision_signed_url"] = {
                    "status": "error", "http_status": r.status_code, "body": r.text[:300],
                }
        except Exception as exc:
            results["test2_vision_signed_url"] = _err(exc)
    else:
        results["test2_vision_signed_url"] = {"status": "skipped", "reason": "no photo file found"}

    # ── TEST 3: groq_whisper_accepts_signed_url ───────────────────────────────
    # NOTE (2026-07, third run): the dummy "_unused" file part caused Groq to
    # reject the whole request with "unknown param `_unused`" — Groq validates
    # every multipart field by name and doesn't silently ignore unrecognized
    # parts. Fix: put `model` and `url` themselves inside `files=` as
    # (None, value) tuples, which is httpx's documented way to send plain
    # form fields as multipart parts without introducing any extra field
    # name Groq doesn't expect. No `data=` dict is used at all this time —
    # every field, including url, goes through the multipart encoder.
    if voice_path:
        try:
            t0 = time.monotonic()
            url = await _signed_url(voice_path)
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    files={
                        "model": (None, "whisper-large-v3"),
                        "url": (None, url),
                    },
                )
            if r.status_code == 200:
                text = r.json().get("text", "")
                results["test3_whisper_signed_url"] = _ok(
                    f"200 in {time.monotonic()-t0:.2f}s, transcript={text[:120]!r}"
                )
            else:
                results["test3_whisper_signed_url"] = {
                    "status": "error", "http_status": r.status_code, "body": r.text[:300],
                }
        except Exception as exc:
            results["test3_whisper_signed_url"] = _err(exc)
    else:
        results["test3_whisper_signed_url"] = {"status": "skipped", "reason": "no voice file found"}

    # ── TEST 4: bytes path via pure files= (no data=) ─────────────────────────
    # Purpose: test 1 (above) confirmed the OGG/Opus codec + filename-extension
    # fix using files={"file": ...} MIXED with data={"model": ...}. Test 3
    # separately confirmed that the URL path needs model/url BOTH inside
    # files= as (None, value) tuples, with no data= at all — mixing files=
    # and data= there produced "Content-Type isn't multipart/form-data".
    # speech_to_text.py's transcribe() now uses the pure-files=-no-data=
    # shape for BOTH the URL path and the bytes path, for consistency — but
    # that specific combination (bytes/file part alongside (None, value)
    # parts, still no data=) was never itself tested against the real API;
    # it was inferred from test 3's finding, not confirmed the way test 1's
    # mixed shape was. This test closes that gap directly, so the code and
    # the test suite are checking the same request shape rather than two
    # similar-but-different ones.
    if voice_path:
        try:
            t0 = time.monotonic()
            loop = asyncio.get_event_loop()
            raw = await loop.run_in_executor(
                None, lambda: supabase.storage.from_(settings.attachment_bucket).download(voice_path)
            )
            _forced_name = voice_path.rsplit("/", 1)[-1].rsplit(".", 1)[0] + ".ogg"
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    files={
                        "model": (None, "whisper-large-v3"),
                        "file": (_forced_name, raw, "audio/ogg"),
                    },
                )
            if r.status_code == 200:
                text = r.json().get("text", "")
                results["test4_whisper_bytes_pure_files"] = _ok(
                    f"200 in {time.monotonic()-t0:.2f}s, transcript={text[:120]!r}"
                )
            else:
                results["test4_whisper_bytes_pure_files"] = {
                    "status": "error", "http_status": r.status_code, "body": r.text[:300],
                }
        except Exception as exc:
            results["test4_whisper_bytes_pure_files"] = _err(exc)
    else:
        results["test4_whisper_bytes_pure_files"] = {"status": "skipped", "reason": "no voice file found"}

    results["_summary"] = {
        "ok": sum(1 for k, v in results.items() if not k.startswith("_") and v.get("status") == "ok"),
        "error": sum(1 for k, v in results.items() if not k.startswith("_") and v.get("status") == "error"),
    }
    return results