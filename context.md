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

from dataclasses import dataclass
from contracts.shared_types import EPKDecision

_DENY_THRESHOLD: float = 0.001    # меньше $0.001 → DENY
_DEGRADE_THRESHOLD: float = 0.30  # больше $0.30 → DEGRADE


@dataclass(frozen=True)
class EPKInput:
    estimated_cost: float
    user_balance: float


@dataclass(frozen=True)
class EPKOutput:
    decision: EPKDecision
    reason: str


def evaluate(epk_input: EPKInput) -> EPKOutput:
    cost = epk_input.estimated_cost
    balance = epk_input.user_balance

    # нет баланса совсем
    if balance <= 0 and cost > _DENY_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    # баланс есть но не хватает
    if cost > balance:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    if cost > _DEGRADE_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DEGRADE,
            reason=f"Cost {cost:.6f} exceeds degrade threshold {_DEGRADE_THRESHOLD}",
        )

    return EPKOutput(decision=EPKDecision.ALLOW, reason="OK")



# core/kernel/decision_matrix.py

from contracts.shared_types import Tier

# ─── TIER THRESHOLDS (USD) ───────────────────────────────────────────────────

_FAST_CEILING: float = 0.05
_GENERAL_CEILING: float = 0.30


def select_tier(estimated_cost: float) -> Tier:
    """
    Select execution tier based on estimated cost.
    Called by orchestrator after EPK returns ALLOW or DEGRADE.
    """
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    elif estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    else:
        return Tier.HEAVY



# core/kernel/cost_model.py

from contracts.shared_types import Tier, Complexity

# ─── PRICING TABLES ─────────────────────────────────────────────────────────
# All rates in USD per 1M tokens

MODEL_RATES: dict[str, dict[str, float]] = {
    Tier.FAST:    {"input": 0.25,  "output": 0.9},
    Tier.GENERAL: {"input": 2.5,   "output": 10.0},
    Tier.HEAVY:   {"input": 8.0,   "output": 30.0},
}

EMBEDDING_RATES: dict[str, float] = {
    "large": 0.1,
    "small": 0.02,
}

RERANK_RATE: float = 1.0

# ─── OUTPUT ESTIMATION ───────────────────────────────────────────────────────

COMPLEXITY_MULTIPLIER: dict[str, float] = {
    Complexity.LOW:      1.2,
    Complexity.MEDIUM:   1.8,
    Complexity.HIGH:     2.5,
    Complexity.CRITICAL: 3.0,
}

MAX_OUTPUT_CAP: dict[str, int] = {
    Tier.FAST:    300,
    Tier.GENERAL: 1200,
    Tier.HEAVY:   3000,
}


def estimate_output_tokens(
    input_tokens: int,
    complexity: Complexity,
    tier: Tier,
) -> int:
    """
    Estimate output token count before execution.
    Used by EPK for pre-flight cost check.
    """
    raw = int(input_tokens * COMPLEXITY_MULTIPLIER[complexity])
    return min(raw, MAX_OUTPUT_CAP[tier])


# ─── COST ESTIMATION (PRE-EXECUTION) ────────────────────────────────────────

def estimate_cost(
    input_tokens: int,
    estimated_output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    """
    Estimated cost before LLM execution.
    Used by EPK to make ALLOW / DENY / DEGRADE decision.
    Returns USD.
    """
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + estimated_output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000


# ─── ACTUAL COST (POST-EXECUTION) ────────────────────────────────────────────

def actual_cost(
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    """
    Actual cost after LLM execution with real token counts.
    Used by usage_meter for billing and TON deduction.
    Returns USD.
    """
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000



# core/kernel/policy_registry.py

from dataclasses import dataclass
from contracts.shared_types import Tier


@dataclass(frozen=True)
class TierPolicy:
    max_input_tokens: int
    max_output_tokens: int
    timeout_seconds: float


@dataclass(frozen=True)
class PolicyRegistry:
    # EPK thresholds
    degrade_threshold_usd: float
    deny_above_balance: bool

    # Tier policies
    tier_policies: dict[str, TierPolicy]

    # Rate limiting (requests per minute per user)
    rate_limit_rpm: int


# ─── ACTIVE POLICY (v4.7) ────────────────────────────────────────────────────

ACTIVE_POLICY = PolicyRegistry(
    degrade_threshold_usd=0.30,
    deny_above_balance=True,

    tier_policies={
        Tier.FAST: TierPolicy(
            max_input_tokens=4_096,
            max_output_tokens=300,
            timeout_seconds=10.0,
        ),
        Tier.GENERAL: TierPolicy(
            max_input_tokens=16_384,
            max_output_tokens=1_200,
            timeout_seconds=30.0,
        ),
        Tier.HEAVY: TierPolicy(
            max_input_tokens=65_536,
            max_output_tokens=3_000,
            timeout_seconds=120.0,
        ),
    },

    rate_limit_rpm=30,
)



# core/execution/orchestrator.py

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent, classify
from cognition.multi_agent_coordinator import CoordinationResult, coordinate, plan_agents
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from contracts.shared_types import Complexity, EPKDecision, Tier
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.prompt_engine import PromptContext, build_messages

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorRequest:
    user_message: str
    user_balance: float
    input_tokens: int
    complexity: Complexity
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    embedding_tokens: int = 0
    rerank_tokens: int = 0
    embedding_type: str = "large"
    lang: str = "en"


@dataclass
class UsageRecord:
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    rerank_tokens: int
    tier: Tier
    embedding_type: str
    cost_usd: float


@dataclass
class OrchestratorResult:
    text: str
    tier: Tier
    model: str
    epk_decision: EPKDecision
    usage: UsageRecord
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


def _denied_result(
    reason: str,
    lang: str,
    tier: Tier = Tier.FAST,
    input_tokens: int = 0,
    embedding_tokens: int = 0,
    rerank_tokens: int = 0,
    embedding_type: str = "large",
    epk_decision: EPKDecision = EPKDecision.DENY,
) -> OrchestratorResult:
    synthesis = synthesize(SynthesisInput(
        raw_text="",
        intent=None,
        tier=tier,
        denied=True,
        deny_reason=reason,
        lang=lang,
    ))
    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model="",
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=input_tokens,
            output_tokens=0,
            embedding_tokens=embedding_tokens,
            rerank_tokens=rerank_tokens,
            tier=tier,
            embedding_type=embedding_type,
            cost_usd=0.0,
        ),
        denied=True,
        deny_reason=reason,
        lang=lang,
    )


# intents that always need GENERAL tier minimum
_HEAVY_INTENTS = {Intent.CODE, Intent.ANALYSIS, Intent.MATH}
_TOOL_INTENTS = {Intent.WEATHER, Intent.SEARCH}


async def _run_tool(intent_result, lang: str) -> str | None:
    if not intent_result.requires_tools or not intent_result.tool_name:
        return None

    logger.error("TOOL DEBUG: name=%s params=%s requires_tools=%s",
                 intent_result.tool_name,
                 intent_result.tool_params,
                 intent_result.requires_tools)

    try:
        from external.web_tools import run_tool
        result = await run_tool(
            tool_name=intent_result.tool_name,
            params=intent_result.tool_params,
            lang=lang,
        )
        logger.info("Tool executed OK", extra={
            "tool": intent_result.tool_name,
            "result": result[:100] if result else None,
        })
        return result
    except Exception as exc:
        import traceback
        logger.error("Tool execution failed FULL: %s\n%s",
                     str(exc),
                     traceback.format_exc())
        return None


async def run(request: OrchestratorRequest) -> OrchestratorResult:
    logger.info("Orchestrator start", extra={
        "user_message_len": len(request.user_message),
        "input_tokens": request.input_tokens,
        "complexity": request.complexity,
        "lang": request.lang,
    })

    try:
        # ── step 1: intent ────────────────────────────────
        intent_result = classify(request.user_message)
        logger.info("Intent classified", extra={
            "intent": intent_result.intent,
            "requires_tools": intent_result.requires_tools,
            "tool_name": intent_result.tool_name,
        })

        # ── step 2: tool execution (weather/search) ───────
        tool_output: str | None = None
        if intent_result.requires_tools:
            tool_output = await _run_tool(intent_result, request.lang)
            logger.info("Tool output", extra={
                "has_output": tool_output is not None,
                "len": len(tool_output) if tool_output else 0,
            })

        # ── step 3: estimate output tokens ───────────────
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            Tier.GENERAL,
        )

        # ── step 4: estimate cost ─────────────────────────
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=Tier.GENERAL,
            embedding_type=request.embedding_type,
        )

        # ── step 5: EPK ───────────────────────────────────
        epk_out = evaluate(EPKInput(
            estimated_cost=estimated,
            user_balance=request.user_balance,
        ))

        logger.info("EPK decision", extra={
            "decision": epk_out.decision,
            "estimated_cost": estimated,
            "balance": request.user_balance,
        })

        if epk_out.decision == EPKDecision.DENY:
            return _denied_result(
                reason="insufficient_balance",
                lang=request.lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── step 6: select tier ───────────────────────────
        tier = select_tier(estimated)

        if epk_out.decision == EPKDecision.DEGRADE:
            tier = Tier.FAST
            logger.info("EPK DEGRADE: forcing FAST tier")
        elif intent_result.intent in _HEAVY_INTENTS:
            # code/math/analysis always get at least GENERAL
            if tier == Tier.FAST:
                tier = Tier.GENERAL
                logger.info("Intent upgrade: FAST → GENERAL", extra={
                    "intent": intent_result.intent,
                })

        # ── step 7: reasoning strategy ────────────────────
        strategy = select_strategy(intent_result.intent, tier)

        # ── step 8: agent plan ────────────────────────────
        plan = plan_agents(intent_result.intent, tier, strategy)

        # ── step 9: build prompt ──────────────────────────
        # inject tool output into context if available
        retrieved_context = request.retrieved_context
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        # for tool-only intents (weather/search) skip LLM if tool succeeded
        if intent_result.intent in _TOOL_INTENTS and tool_output:
            logger.info("Tool-only response, skipping LLM")
            synthesis = synthesize(SynthesisInput(
                raw_text=tool_output,
                intent=intent_result.intent,
                tier=tier,
                lang=request.lang,
            ))
            return OrchestratorResult(
                text=synthesis.text,
                tier=tier,
                model="tool",
                epk_decision=epk_out.decision,
                usage=UsageRecord(
                    input_tokens=request.input_tokens,
                    output_tokens=0,
                    embedding_tokens=request.embedding_tokens,
                    rerank_tokens=request.rerank_tokens,
                    tier=tier,
                    embedding_type=request.embedding_type,
                    cost_usd=0.0,
                ),
                lang=request.lang,
            )

        messages = build_messages(PromptContext(
            user_message=(
                f"{strategy.instruction_prefix} {request.user_message}".strip()
                if strategy.instruction_prefix
                else request.user_message
            ),
            system_prompt=request.system_prompt or intent_result.system_prompt,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
        ))

        logger.info("Messages built", extra={"message_count": len(messages)})

        # ── step 10: agent execution ──────────────────────
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
        )

        logger.info("Coordination done", extra={
            "blocked": coordination.blocked,
            "text_len": len(coordination.text),
        })

        if coordination.blocked:
            return _denied_result(
                reason="default_deny",
                lang=request.lang,
                tier=tier,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=epk_out.decision,
            )

        # ── step 11: actual cost ──────────────────────────
        cost = actual_cost(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=tier,
            embedding_type=request.embedding_type,
        )

        usage = UsageRecord(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=tier,
            embedding_type=request.embedding_type,
            cost_usd=cost,
        )

        # ── step 12: synthesize ───────────────────────────
        synthesis = synthesize(SynthesisInput(
            raw_text=coordination.text,
            intent=intent_result.intent,
            tier=tier,
            lang=request.lang,
        ))

        logger.info("Orchestrator complete", extra={
            "tier": tier,
            "model": coordination.model,
            "cost_usd": cost,
            "output_tokens": coordination.output_tokens,
        })

        return OrchestratorResult(
            text=synthesis.text,
            tier=tier,
            model=coordination.model,
            epk_decision=epk_out.decision,
            usage=usage,
            lang=request.lang,
        )

    except Exception as exc:
        logger.error("Orchestrator crashed", extra={"error": str(exc)}, exc_info=True)
        synthesis = synthesize(SynthesisInput(
            raw_text="",
            intent=None,
            tier=Tier.FAST,
            denied=True,
            deny_reason="default_deny",
            lang=request.lang,
        ))
        return OrchestratorResult(
            text=synthesis.text,
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=request.input_tokens,
                output_tokens=0,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                tier=Tier.FAST,
                embedding_type=request.embedding_type,
                cost_usd=0.0,
            ),
            denied=True,
            deny_reason="internal_error",
            lang=request.lang,
        )



# events/event_bus.py

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from events.event_types import BaseEvent, EventName

logger = logging.getLogger(__name__)

Handler = Callable[[BaseEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventName, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    def subscribe(self, event_name: EventName, handler: Handler) -> None:
        """Register a handler for a specific event name."""
        self._handlers[event_name].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Register a handler that receives every event (useful for loggers)."""
        self._wildcard.append(handler)

    async def publish(self, event: BaseEvent) -> None:
        """
        Fire event to all subscribers.
        Always non-blocking — handlers run as background tasks.
        publish() itself never raises.
        """
        handlers = self._handlers.get(event.name, []) + self._wildcard

        for handler in handlers:
            asyncio.create_task(self._safe_call(handler, event))

    @staticmethod
    async def _safe_call(handler: Handler, event: BaseEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.warning(
                "Event handler failed",
                extra={
                    "handler": handler.__qualname__,
                    "event": event.name,
                    "error": str(exc),
                },
            )


# Singleton
event_bus = EventBus()



# events/event_store.py

import json
import logging
from datetime import timezone

from redis.asyncio import Redis

from events.event_types import BaseEvent

logger = logging.getLogger(__name__)

_KEY_PREFIX = "events"
_KEY_ALL = f"{_KEY_PREFIX}:all"
_KEY_USER = f"{_KEY_PREFIX}:user"
_TTL_SECONDS = 60 * 60 * 24 * 30   # 30 days


def _serialize(event: BaseEvent) -> str:
    return json.dumps({
        "event_id":  event.event_id,
        "name":      event.name,
        "user_id":   event.user_id,
        "payload":   event.payload,
        "timestamp": event.timestamp.isoformat(),
    })


class EventStore:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def append(self, event: BaseEvent) -> None:
        """
        Append event to the global stream and user-specific stream.
        Fire-and-forget safe — errors are logged, never raised.
        """
        try:
            score = event.timestamp.replace(tzinfo=timezone.utc).timestamp()
            data = _serialize(event)

            pipe = self._redis.pipeline()

            # global stream
            pipe.zadd(_KEY_ALL, {data: score})
            pipe.expire(_KEY_ALL, _TTL_SECONDS)

            # per-user stream
            if event.user_id is not None:
                user_key = f"{_KEY_USER}:{event.user_id}"
                pipe.zadd(user_key, {data: score})
                pipe.expire(user_key, _TTL_SECONDS)

            await pipe.execute()

        except Exception as exc:
            logger.warning(
                "EventStore.append failed",
                extra={"event": event.name, "error": str(exc)},
            )

    async def read_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Read latest events from global stream. Used by event_replay only."""
        try:
            raw = await self._redis.zrevrange(
                _KEY_ALL, offset, offset + limit - 1
            )
            return [json.loads(r) for r in raw]
        except Exception as exc:
            logger.warning("EventStore.read_all failed", extra={"error": str(exc)})
            return []

    async def read_user(
        self,
        user_id: int,
        limit: int = 50,
    ) -> list[dict]:
        """Read latest events for a specific user. Used by event_replay only."""
        try:
            user_key = f"{_KEY_USER}:{user_id}"
            raw = await self._redis.zrevrange(user_key, 0, limit - 1)
            return [json.loads(r) for r in raw]
        except Exception as exc:
            logger.warning("EventStore.read_user failed", extra={"error": str(exc)})
            return []



# events/event_types.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


# ─── EVENT NAMES ─────────────────────────────────────────────────────────────

class EventName(str, Enum):
    # transport
    UPDATE_RECEIVED      = "update.received"
    UPDATE_REJECTED      = "update.rejected"

    # auth
    AUTH_PASSED          = "auth.passed"
    AUTH_FAILED          = "auth.failed"

    # EPK
    EPK_ALLOW            = "epk.allow"
    EPK_DENY             = "epk.deny"
    EPK_DEGRADE          = "epk.degrade"

    # execution
    EXECUTION_STARTED    = "execution.started"
    EXECUTION_COMPLETED  = "execution.completed"
    EXECUTION_FAILED     = "execution.failed"

    # LLM
    LLM_CALLED           = "llm.called"
    LLM_FALLBACK         = "llm.fallback"

    # retrieval
    RETRIEVAL_STARTED    = "retrieval.started"
    RETRIEVAL_COMPLETED  = "retrieval.completed"

    # memory
    MEMORY_READ          = "memory.read"
    MEMORY_WRITTEN       = "memory.written"

    # payments
    BALANCE_CHECKED      = "balance.checked"
    BALANCE_DEDUCTED     = "balance.deducted"
    BALANCE_INSUFFICIENT = "balance.insufficient"


# ─── BASE EVENT ───────────────────────────────────────────────────────────────

@dataclass
class BaseEvent:
    name: EventName
    user_id: int | None = None
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── TYPED EVENTS ────────────────────────────────────────────────────────────

@dataclass
class UpdateReceivedEvent(BaseEvent):
    name: EventName = EventName.UPDATE_RECEIVED


@dataclass
class AuthFailedEvent(BaseEvent):
    name: EventName = EventName.AUTH_FAILED


@dataclass
class EPKDecisionEvent(BaseEvent):
    """Covers ALLOW / DENY / DEGRADE — set name accordingly."""
    name: EventName = EventName.EPK_ALLOW


@dataclass
class ExecutionCompletedEvent(BaseEvent):
    name: EventName = EventName.EXECUTION_COMPLETED


@dataclass
class ExecutionFailedEvent(BaseEvent):
    name: EventName = EventName.EXECUTION_FAILED


@dataclass
class LLMCalledEvent(BaseEvent):
    name: EventName = EventName.LLM_CALLED


@dataclass
class LLMFallbackEvent(BaseEvent):
    name: EventName = EventName.LLM_FALLBACK


@dataclass
class BalanceDeductedEvent(BaseEvent):
    name: EventName = EventName.BALANCE_DEDUCTED


@dataclass
class BalanceInsufficientEvent(BaseEvent):
    name: EventName = EventName.BALANCE_INSUFFICIENT