# Текущая архитектура,не включая Dockerfile, docker-compose.yml, pyproject.toml, railway.toml, .github/worflows/ci.yml (они будут в конце). Все файлы готовы и помечены ×, но желательно их добить и/или переписать/улучшить в случае и по мере необходимости.


# Архитектура v5.7


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




# app/settings.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── CORE ───────────────────────────────────────────
    bot_token: str = Field(..., description="Telegram bot token")
    jwt_secret: str = Field(..., description="JWT signing secret")
    encryption_key: str = Field(..., description="Fernet encryption key")
    webhook_url: str = Field(..., description="Public webhook URL")
    allowed_origins: str = Field("*", description="Comma-separated allowed origins")

    # ─── LLM PROVIDERS ──────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key")
    hf_token: str = Field(..., description="HuggingFace token")

    # ─── MEMORY / STORAGE ───────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")

    # ─── EXTERNAL SERVICES ──────────────────────────────
    brevo_api_key: str = Field("", description="Brevo email API key")
    mapbox_token: str = Field("", description="Mapbox token")
    openweather_api_key: str = Field("", description="OpenWeather API key")
    serpapi_key: str = Field("", description="SerpAPI key")
    sentry_dsn: str = Field("", description="Sentry DSN")

    # ─── ECONOMY / TON ──────────────────────────────────
    ton_wallet: str = Field("", description="TON wallet address")

    # ─── RUNTIME ────────────────────────────────────────
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field("production", description="Environment name")


# Singleton — import this everywhere
settings = Settings()



# transport/telegram/webhook.py

import logging
import re

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, status

from app.settings import settings
from transport.telegram.auth_middleware import verify_update, verify_webhook_secret
from transport.telegram.callback_handler import CallbackAction, parse_callback
from transport.telegram.message_router import UpdateType, classify_update
from transport.telegram.update_handler import handle_message

logger = logging.getLogger(__name__)

router = APIRouter()

_TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"

# secret_token: only A-Z a-z 0-9 _ - allowed, max 256 chars
_WEBHOOK_SECRET = re.sub(r"[^A-Za-z0-9_\-]", "_", settings.bot_token)[:256]


async def _send_message(chat_id: int, text: str) -> None:
    if not text:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10.0,
        )


async def _answer_callback(callback_query_id: str, text: str = "") -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5.0,
        )


def _get_chat_id(update: dict) -> int | None:
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        chat = msg.get("chat", {})
        if chat.get("id"):
            return chat["id"]
    cq = update.get("callback_query", {})
    msg = cq.get("message", {})
    return msg.get("chat", {}).get("id")


def _detect_lang(update: dict) -> str:
    for key in ("message", "edited_message", "callback_query"):
        entry = update.get(key, {})
        user = entry.get("from") or {}
        code = user.get("language_code", "")
        if code:
            return code.split("-")[0].lower()
    return "en"


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    # ── secret token check (optional — skip if not sent) ──
    if x_telegram_bot_api_secret_token:
        if not verify_webhook_secret(x_telegram_bot_api_secret_token, _WEBHOOK_SECRET):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:
        update: dict = await request.json()
    except Exception as exc:
        logger.error("Failed to parse update JSON", extra={"error": str(exc)})
        return {"ok": True}

    update_type = classify_update(update)

    if update_type == UpdateType.UNKNOWN:
        return {"ok": True}

    auth = verify_update(update)
    if not auth.allowed:
        logger.warning("Rejected update", extra={"reason": auth.reason})
        return {"ok": True}

    chat_id = _get_chat_id(update)
    user_id = auth.user_id
    lang = _detect_lang(update)
    supabase = request.app.state.supabase

    # ── rate limiting ─────────────────────────────────────
    from cognition.response_synthesizer import get_system_message
    from security.rate_limiter import get_rate_limiter

    limiter = get_rate_limiter()
    if limiter and not await limiter.is_allowed(user_id):
        if chat_id:
            await _send_message(chat_id, get_system_message("rate_limited", lang))
        return {"ok": True}

    # ── real balance ──────────────────────────────────────
    user_balance = 0.0
    try:
        from payments.access_controller import AccessController
        ac = AccessController(supabase)
        balance_result = await ac.get_balance(user_id)
        user_balance = balance_result.balance_usd
    except Exception as exc:
        logger.error("Balance fetch failed", extra={"error": str(exc)})

    # ── message handling ──────────────────────────────────
    if update_type in (UpdateType.MESSAGE, UpdateType.EDITED_MESSAGE):
        try:
            result = await handle_message(
                update=update,
                update_type=update_type,
                user_id=user_id,
                user_balance=user_balance,
                lang=lang,
                supabase=supabase,
            )
        except Exception as exc:
            logger.error("handle_message crashed", extra={"error": str(exc)})
            if chat_id:
                await _send_message(
                    chat_id,
                    get_system_message("no_response", lang),
                )
            return {"ok": True}

        # ── billing ───────────────────────────────────────
        if not result.denied and result.usage.cost_usd > 0:
            try:
                from payments.access_controller import AccessController
                from payments.usage_meter import UsageEntry, UsageMeter

                ac = AccessController(supabase)
                await ac.deduct(user_id, result.usage.cost_usd)

                meter = UsageMeter(supabase)
                billed = meter.compute_billed(result.usage.cost_usd)
                await meter.record(UsageEntry(
                    user_id=user_id,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    embedding_tokens=result.usage.embedding_tokens,
                    rerank_tokens=result.usage.rerank_tokens,
                    tier=result.usage.tier,
                    embedding_type=result.usage.embedding_type,
                    raw_cost_usd=result.usage.cost_usd,
                    billed_cost_usd=billed,
                    model=result.model,
                    lang=result.lang,
                ))
            except Exception as exc:
                logger.error("Billing failed", extra={"error": str(exc)})

        if chat_id:
            await _send_message(chat_id, result.text)

    elif update_type == UpdateType.CALLBACK_QUERY:
        ctx = parse_callback(update, user_id)

        if ctx.action == CallbackAction.BALANCE:
            bal_text = f"💰 Balance: ${user_balance:.2f}"
            await _answer_callback(ctx.callback_query_id, bal_text)
        elif ctx.action == CallbackAction.HELP:
            await _answer_callback(
                ctx.callback_query_id,
                get_system_message("help_display", lang),
            )
        elif ctx.action == CallbackAction.CANCEL:
            await _answer_callback(
                ctx.callback_query_id,
                get_system_message("cancelled", lang),
            )
        else:
            await _answer_callback(ctx.callback_query_id)

    return {"ok": True}


async def register_webhook() -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_TELEGRAM_API}/setWebhook",
            json={
                "url": f"{settings.webhook_url}/webhook",
                "secret_token": _WEBHOOK_SECRET,
                "allowed_updates": ["message", "edited_message", "callback_query"],
            },
            timeout=10.0,
        )
        data = response.json()
        ok = data.get("ok", False)
        logger.info("Webhook registration", extra={"ok": ok, "response": data})
        return ok



# transport/telegram/update_handler.py

import logging

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, UsageRecord, run
from transport.telegram.message_router import UpdateType, extract_text

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _classify_complexity(text: str) -> Complexity:
    has_code = "```" in text or "    " in text
    has_json = "{" in text and "}" in text
    length = len(text)

    if has_code and has_json:
        return Complexity.CRITICAL
    if has_code or has_json:
        return Complexity.HIGH
    if length > 500:
        return Complexity.MEDIUM
    return Complexity.LOW


async def handle_message(
    update: dict,
    update_type: UpdateType,
    user_id: int,
    user_balance: float,
    lang: str = "en",
    supabase=None,          # injected from webhook
) -> OrchestratorResult:
    text = extract_text(update)

    if not text:
        logger.info("Empty text update ignored", extra={"user_id": user_id})
        return OrchestratorResult(
            text="",
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                rerank_tokens=0,
                tier=Tier.FAST,
                embedding_type="large",
                cost_usd=0.0,
            ),
            denied=True,
            deny_reason="empty_message",
            lang=lang,
        )

    input_tokens = _estimate_tokens(text)
    complexity = _classify_complexity(text)

    # ── load conversation history ─────────────────────────
    conversation_history: list[dict] | None = None
    history_store = None

    if supabase is not None:
        try:
            from memory.conversation_history import ConversationHistory
            history_store = ConversationHistory(supabase)
            conversation_history = await history_store.get_history(user_id)
            logger.info("History loaded", extra={
                "user_id": user_id,
                "turns": len(conversation_history),
            })
        except Exception as exc:
            logger.error("History load failed", extra={"error": str(exc)})
            conversation_history = None

    logger.info("Handling message", extra={
        "user_id": user_id,
        "input_tokens": input_tokens,
        "complexity": complexity,
        "lang": lang,
    })

    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        input_tokens=input_tokens,
        complexity=complexity,
        lang=lang,
        conversation_history=conversation_history,
    )

    result = await run(request)

    # ── save turns to history ─────────────────────────────
    if history_store is not None and not result.denied:
        try:
            await history_store.append(user_id, "user", text)
            if result.text:
                await history_store.append(user_id, "assistant", result.text)
        except Exception as exc:
            logger.error("History save failed", extra={"error": str(exc)})

    return result



# transport/telegram/message_router.py

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    MESSAGE = "message"
    CALLBACK_QUERY = "callback_query"
    EDITED_MESSAGE = "edited_message"
    UNKNOWN = "unknown"


def classify_update(update: dict) -> UpdateType:
    """Classify incoming Telegram update by type."""
    if "message" in update:
        return UpdateType.MESSAGE
    if "callback_query" in update:
        return UpdateType.CALLBACK_QUERY
    if "edited_message" in update:
        return UpdateType.EDITED_MESSAGE
    return UpdateType.UNKNOWN


def extract_text(update: dict) -> str:
    """Extract plain text from message or edited_message."""
    for key in ("message", "edited_message"):
        msg = update.get(key, {})
        text = msg.get("text") or msg.get("caption") or ""
        if text:
            return text
    return ""


def extract_callback_data(update: dict) -> str:
    """Extract callback_data from callback_query update."""
    return update.get("callback_query", {}).get("data", "")



# transport/telegram/callback_handler.py

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CallbackAction(str, Enum):
    BALANCE = "balance"
    HELP = "help"
    CANCEL = "cancel"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CallbackContext:
    action: CallbackAction
    payload: str          # anything after the first ":" in callback_data
    callback_query_id: str
    user_id: int


def parse_callback(update: dict, user_id: int) -> CallbackContext:
    """
    Parse callback_query update into a typed CallbackContext.
    callback_data format: "action" or "action:payload"
    """
    cq = update.get("callback_query", {})
    callback_query_id = cq.get("id", "")
    raw_data = cq.get("data", "")

    parts = raw_data.split(":", 1)
    action_str = parts[0] if parts else ""
    payload = parts[1] if len(parts) > 1 else ""

    try:
        action = CallbackAction(action_str)
    except ValueError:
        logger.warning("Unknown callback action", extra={"raw_data": raw_data})
        action = CallbackAction.UNKNOWN

    return CallbackContext(
        action=action,
        payload=payload,
        callback_query_id=callback_query_id,
        user_id=user_id,
    )



#transport/telegram/auth_middleware.py

import hashlib
import hmac
import logging
from dataclasses import dataclass

from app.settings import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthResult:
    allowed: bool
    user_id: int | None = None
    username: str | None = None
    reason: str = ""


def _extract_user(update: dict) -> tuple[int | None, str | None]:
    """Pull user_id and username from any update type."""
    for key in ("message", "callback_query", "edited_message"):
        entry = update.get(key)
        if entry:
            user = entry.get("from") or {}
            return user.get("id"), user.get("username")
    return None, None


def verify_update(update: dict) -> AuthResult:
    """
    Validate incoming Telegram update.
    Currently: extract user_id and confirm it exists.
    Extend here for whitelist / ban checks using Redis or Supabase.
    """
    user_id, username = _extract_user(update)

    if user_id is None:
        logger.warning("Update with no user_id rejected")
        return AuthResult(allowed=False, reason="no_user_id")

    return AuthResult(
        allowed=True,
        user_id=user_id,
        username=username,
    )


def verify_webhook_secret(token: str, expected: str) -> bool:
    """
    Compare webhook secret token using constant-time comparison.
    Pass X-Telegram-Bot-Api-Secret-Token header value here.
    """
    return hmac.compare_digest(token.encode(), expected.encode())



# core/kernel/execution_policy_kernel.py