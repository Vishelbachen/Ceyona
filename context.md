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



# events/event_dispatcher.py

import logging

from events.event_bus import EventBus
from events.event_store import EventStore
from events.event_types import BaseEvent

logger = logging.getLogger(__name__)


async def _log_handler(event: BaseEvent) -> None:
    """Structured log for every event — observability only."""
    logger.info(
        "event",
        extra={
            "event_id":  event.event_id,
            "name":      event.name,
            "user_id":   event.user_id,
            "payload":   event.payload,
            "timestamp": event.timestamp.isoformat(),
        },
    )


def setup_dispatcher(bus: EventBus, store: EventStore) -> None:
    """
    Register all system handlers on the bus.
    Call once from bootstrap.py after Redis is ready.
    """

    async def _store_handler(event: BaseEvent) -> None:
        await store.append(event)

    # every event → structured log
    bus.subscribe_all(_log_handler)

    # every event → persistent store
    bus.subscribe_all(_store_handler)

    logger.info("EventDispatcher: handlers registered")



# events/event_replay.py

import logging
from typing import Awaitable, Callable

from events.event_store import EventStore
from events.event_types import BaseEvent, EventName

logger = logging.getLogger(__name__)

ReplayHandler = Callable[[dict], Awaitable[None]]


class EventReplay:
    def __init__(self, store: EventStore) -> None:
        self._store = store

    async def replay_all(
        self,
        handler: ReplayHandler,
        limit: int = 100,
    ) -> int:
        """
        Replay global event stream to handler.
        Returns number of events replayed.
        """
        events = await self._store.read_all(limit=limit)
        for event in events:
            await self._safe_call(handler, event)
        logger.info("Replay complete", extra={"count": len(events)})
        return len(events)

    async def replay_user(
        self,
        user_id: int,
        handler: ReplayHandler,
        limit: int = 50,
    ) -> int:
        """
        Replay event stream for a specific user.
        Returns number of events replayed.
        """
        events = await self._store.read_user(user_id=user_id, limit=limit)
        for event in events:
            await self._safe_call(handler, event)
        logger.info(
            "User replay complete",
            extra={"user_id": user_id, "count": len(events)},
        )
        return len(events)

    async def replay_by_name(
        self,
        user_id: int,
        event_name: EventName,
        handler: ReplayHandler,
        limit: int = 50,
    ) -> int:
        """
        Replay only events matching a specific name for a user.
        Filtering is done in-process (store has no query capability by design).
        """
        events = await self._store.read_user(user_id=user_id, limit=limit)
        filtered = [e for e in events if e.get("name") == event_name]
        for event in filtered:
            await self._safe_call(handler, event)
        return len(filtered)

    @staticmethod
    async def _safe_call(handler: ReplayHandler, event: dict) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.warning(
                "Replay handler failed",
                extra={"event": event.get("name"), "error": str(exc)},
            )



# cognition/intent_engine.py

from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    QUESTION        = "question"
    INSTRUCTION     = "instruction"
    CODE            = "code"
    ANALYSIS        = "analysis"
    CREATIVE        = "creative"
    CONVERSATION    = "conversation"
    MATH            = "math"
    WEATHER         = "weather"
    SEARCH          = "search"
    UNKNOWN         = "unknown"


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float
    system_prompt: str
    requires_retrieval: bool
    requires_tools: bool
    tool_name: str = ""
    tool_params: dict = None

    def __post_init__(self):
        if self.tool_params is None:
            object.__setattr__(self, "tool_params", {})


_SYSTEM_PROMPTS: dict[Intent, str] = {
    Intent.QUESTION: (
        "You are a precise and concise assistant. "
        "Answer the user's question directly and factually. "
        "If you are unsure, say so explicitly."
    ),
    Intent.INSTRUCTION: (
        "You are a helpful assistant. "
        "Provide clear, numbered step-by-step instructions. "
        "Be complete but concise."
    ),
    Intent.CODE: (
        "You are an expert software engineer. "
        "Write clean, well-commented code. "
        "Always specify the language. Explain your approach briefly."
    ),
    Intent.ANALYSIS: (
        "You are an analytical assistant. "
        "Structure your analysis clearly with key findings first. "
        "Be objective and evidence-based."
    ),
    Intent.CREATIVE: (
        "You are a creative writing assistant. "
        "Be imaginative, engaging, and original. "
        "Match the tone and style the user requests."
    ),
    Intent.CONVERSATION: (
        "You are a friendly and helpful assistant. "
        "Keep responses conversational and appropriately brief."
    ),
    Intent.MATH: (
        "You are a precise mathematical assistant. "
        "Show your work step by step. "
        "State the final answer clearly."
    ),
    Intent.WEATHER: (
        "You are a helpful assistant providing weather information. "
        "Present weather data clearly and concisely."
    ),
    Intent.SEARCH: (
        "You are a helpful assistant. "
        "Summarize search results clearly and concisely."
    ),
    Intent.UNKNOWN: (
        "You are a helpful assistant. "
        "Do your best to understand and respond to the user's request."
    ),
}

_CODE_SIGNALS = (
    "```", "def ", "class ", "import ", "function ", "return ",
    "var ", "const ", "let ", "print(", "console.log", "#!/",
    "напиши код", "напиши скрипт", "write code", "write a script",
    "write a function", "write a program", "fix this code",
    "исправь код", "почини код", "debug", "дебаг",
)
_MATH_SIGNALS = (
    "=", "∑", "∫", "√", "calculate", "solve", "formula",
    "equation", "вычисли", "посчитай", "реши", "сколько будет",
    "how much is", "what is", "%", "процент", "percent",
    "производная", "integral", "matrix", "матрица",
)
_QUESTION_ENDS = ("?", "؟", "？")
_CREATIVE_SIGNALS = (
    "write a", "write me", "poem", "story", "essay",
    "generate", "create a", "напиши", "сочини", "придумай",
    "стихотворение", "рассказ", "сказку", "песню",
)
_ANALYSIS_SIGNALS = (
    "analyse", "analyze", "compare", "evaluate", "review",
    "summarize", "summarise", "проанализируй", "сравни",
    "оцени", "резюмируй", "объясни почему", "explain why",
)
_INSTRUCTION_SIGNALS = (
    "how to", "how do i", "steps to", "guide", "explain how",
    "walk me through", "как", "как сделать", "как установить",
    "как настроить", "покажи как", "научи",
)
_GREETING_SIGNALS = (
    "hello", "hi", "hey", "good morning", "good evening",
    "thanks", "thank you", "привет", "здравствуй", "добрый",
    "спасибо", "пока", "bye", "salut", "hola", "naber",
    "merhaba", "ciao", "こんにちは", "안녕",
)
_WEATHER_SIGNALS = (
    "weather", "погода", "погоду", "температура", "temperature",
    "дождь", "rain", "snow", "снег", "forecast", "прогноз",
    "холодно", "жарко", "тепло", "cold", "hot", "warm",
    "sunny", "cloudy", "облачно", "ветер", "wind",
    "hava", "météo", "wetter", "clima", "meteo",
)
_SEARCH_SIGNALS = (
    "найди", "поищи", "search for", "find", "look up",
    "what happened", "latest", "news", "новости", "что произошло",
    "кто такой", "who is", "что такое", "what is",
    "tell me about", "расскажи о", "информация о",
)


def _extract_city(text: str) -> str:
    """Simple city extraction from weather query."""
    lower = text.lower()
    markers = [
        "в ", "in ", "at ", "for ", "weather in ", "погода в ",
        "погоду в ", "weather at ", "температура в ",
    ]
    for marker in markers:
        idx = lower.find(marker)
        if idx != -1:
            rest = text[idx + len(marker):].strip()
            city = rest.split()[0].rstrip("?.!,")
            if city:
                return city
    # fallback: last word
    words = text.strip().rstrip("?.!").split()
    return words[-1] if words else ""


def classify(text: str) -> IntentResult:
    lower = text.lower().strip()

    # ── weather ──────────────────────────────────────────
    if any(s in lower for s in _WEATHER_SIGNALS):
        city = _extract_city(text)
        return _result(
            Intent.WEATHER, 0.9,
            requires_retrieval=False,
            requires_tools=True,
            tool_name="weather",
            tool_params={"city": city} if city else {},
        )

    # ── code ─────────────────────────────────────────────
    if any(s in text for s in _CODE_SIGNALS):
        return _result(Intent.CODE, 0.9,
                       requires_retrieval=False, requires_tools=False)

    # ── math ─────────────────────────────────────────────
    if any(s in lower for s in _MATH_SIGNALS):
        return _result(Intent.MATH, 0.8,
                       requires_retrieval=False, requires_tools=False)

    # ── analysis ─────────────────────────────────────────
    if any(s in lower for s in _ANALYSIS_SIGNALS):
        return _result(Intent.ANALYSIS, 0.85,
                       requires_retrieval=True, requires_tools=False)

    # ── creative ─────────────────────────────────────────
    if any(s in lower for s in _CREATIVE_SIGNALS):
        return _result(Intent.CREATIVE, 0.85,
                       requires_retrieval=False, requires_tools=False)

    # ── instruction ──────────────────────────────────────
    if any(s in lower for s in _INSTRUCTION_SIGNALS):
        return _result(Intent.INSTRUCTION, 0.85,
                       requires_retrieval=True, requires_tools=False)

    # ── search ───────────────────────────────────────────
    if any(s in lower for s in _SEARCH_SIGNALS):
        return _result(Intent.SEARCH, 0.8,
                       requires_retrieval=False, requires_tools=True,
                       tool_name="search",
                       tool_params={"query": text, "num": 5})

    # ── question ─────────────────────────────────────────
    if any(lower.endswith(e) for e in _QUESTION_ENDS):
        return _result(Intent.QUESTION, 0.8,
                       requires_retrieval=True, requires_tools=False)

    # ── conversation ─────────────────────────────────────
    if any(s in lower for s in _GREETING_SIGNALS):
        return _result(Intent.CONVERSATION, 0.9,
                       requires_retrieval=False, requires_tools=False)

    # ── fallback ─────────────────────────────────────────
    return _result(Intent.UNKNOWN, 0.4,
                   requires_retrieval=True, requires_tools=False)


def _result(
    intent: Intent,
    confidence: float,
    requires_retrieval: bool,
    requires_tools: bool,
    tool_name: str = "",
    tool_params: dict = None,
) -> IntentResult:
    return IntentResult(
        intent=intent,
        confidence=confidence,
        system_prompt=_SYSTEM_PROMPTS[intent],
        requires_retrieval=requires_retrieval,
        requires_tools=requires_tools,
        tool_name=tool_name,
        tool_params=tool_params or {},
    )



# cognition/reasoning_engine.py

from dataclasses import dataclass
from enum import Enum

from cognition.intent_engine import Intent
from contracts.shared_types import Tier


# ─── STRATEGY DEFINITIONS ────────────────────────────────────────────────────

class ReasoningMode(str, Enum):
    DIRECT          = "direct"          # answer immediately, no preamble
    CHAIN_OF_THOUGHT = "chain_of_thought"  # think step by step
    STRUCTURED      = "structured"      # use headers / numbered lists
    EXPLORATORY     = "exploratory"     # consider multiple angles


@dataclass(frozen=True)
class ReasoningStrategy:
    mode: ReasoningMode
    temperature: float          # passed to LLM
    instruction_prefix: str     # prepended to user message if non-empty
    max_reasoning_steps: int    # hint for agent layer


# ─── STRATEGY MATRIX ─────────────────────────────────────────────────────────
# (Intent, Tier) → ReasoningStrategy
# FAST tier always favours DIRECT to stay within token cap.

_STRATEGY_MATRIX: dict[tuple[str, str], ReasoningStrategy] = {

    # ── QUESTION ─────────────────────────────────────────
    (Intent.QUESTION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.QUESTION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.4,
        instruction_prefix="Think carefully, then answer:",
        max_reasoning_steps=3,
    ),
    (Intent.QUESTION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.3,
        instruction_prefix="Think carefully, then answer:",
        max_reasoning_steps=5,
    ),

    # ── CODE ─────────────────────────────────────────────
    (Intent.CODE, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CODE, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),
    (Intent.CODE, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.15,
        instruction_prefix="",
        max_reasoning_steps=5,
    ),

    # ── ANALYSIS ─────────────────────────────────────────
    (Intent.ANALYSIS, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.4,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.ANALYSIS, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.5,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=4,
    ),
    (Intent.ANALYSIS, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.4,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=6,
    ),

    # ── CREATIVE ─────────────────────────────────────────
    (Intent.CREATIVE, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.8,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CREATIVE, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.85,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.CREATIVE, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.9,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),

    # ── MATH ─────────────────────────────────────────────
    (Intent.MATH, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=3,
    ),
    (Intent.MATH, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=5,
    ),
    (Intent.MATH, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.05,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=8,
    ),

    # ── INSTRUCTION ──────────────────────────────────────
    (Intent.INSTRUCTION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.INSTRUCTION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.35,
        instruction_prefix="",
        max_reasoning_steps=4,
    ),
    (Intent.INSTRUCTION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=6,
    ),

    # ── CONVERSATION ─────────────────────────────────────
    (Intent.CONVERSATION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CONVERSATION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CONVERSATION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
}

_DEFAULT_STRATEGY = ReasoningStrategy(
    mode=ReasoningMode.DIRECT,
    temperature=0.5,
    instruction_prefix="",
    max_reasoning_steps=2,
)


def select_strategy(intent: Intent, tier: Tier) -> ReasoningStrategy:
    """
    Select reasoning strategy for a given intent + tier combination.
    Pure function. No I/O. No state.
    """
    return _STRATEGY_MATRIX.get((intent, tier), _DEFAULT_STRATEGY)



# cognition/multi_agent_coordinator.py

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

import agents.creative_agent as creative_agent
import agents.deep_agent as deep_agent
import agents.fast_agent as fast_agent
from agents.consensus_engine import ConsensusResult, resolve
from agents.fast_agent import AgentResult
from agents.safety_agent import SafetyResult, check as safety_check
from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


# ─── AGENT IDENTIFIERS ───────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST     = "fast_agent"
    DEEP     = "deep_agent"
    CREATIVE = "creative_agent"
    SAFETY   = "safety_agent"


# ─── AGENT PLAN ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    validators: list[AgentType] = field(default_factory=list)
    use_consensus: bool = False
    parallel: bool = False


# ─── COORDINATION RESULT ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class CoordinationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    blocked: bool = False
    block_reason: str = ""


# ─── PLAN SELECTION ──────────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select which agents to activate.
    Pure function. No I/O. No state. No LLM calls.
    """
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.FAST, AgentType.SAFETY],
            use_consensus=True,
            parallel=True,
        )

    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if intent in (Intent.CODE, Intent.MATH, Intent.ANALYSIS):
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    return AgentPlan(
        primary=AgentType.FAST,
        validators=[AgentType.SAFETY],
        use_consensus=False,
        parallel=False,
    )


# ─── AGENT DISPATCHER ────────────────────────────────────────────────────────

async def _run_agent(agent_type: AgentType, messages: list[dict]) -> AgentResult:
    """Dispatch to the correct agent module."""
    if agent_type == AgentType.FAST:
        return await fast_agent.run(messages)
    if agent_type == AgentType.DEEP:
        return await deep_agent.run(messages)
    if agent_type == AgentType.CREATIVE:
        return await creative_agent.run(messages)
    # safety_agent is always sync check — never dispatched as LLM agent
    return AgentResult(text="", model="", input_tokens=0, output_tokens=0, success=False)


# ─── MAIN COORDINATOR ────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
) -> CoordinationResult:
    """
    Execute agent plan and return final result.
    Handles: safety check, parallel/sequential execution, consensus.
    """

    # ── safety check first (always sync, no LLM) ────────
    safety: SafetyResult = safety_check(user_message)
    if not safety.safe:
        logger.warning("Safety block", extra={"reason": safety.reason})
        return CoordinationResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            blocked=True,
            block_reason=safety.reason,
        )

    # ── primary agent execution ──────────────────────────
    primary_result = await _run_agent(plan.primary, messages)

    # ── consensus path (HEAVY tier) ──────────────────────
    if plan.use_consensus:
        validator_types = [v for v in plan.validators if v != AgentType.SAFETY]

        if plan.parallel and validator_types:
            tasks = [_run_agent(vt, messages) for vt in validator_types]
            validator_results: list[AgentResult] = await asyncio.gather(*tasks)
        else:
            validator_results = []
            for vt in validator_types:
                validator_results.append(await _run_agent(vt, messages))

        all_results = [primary_result, *validator_results]
        consensus: ConsensusResult = resolve(all_results)

        return CoordinationResult(
            text=consensus.text,
            model=consensus.model,
            input_tokens=consensus.input_tokens,
            output_tokens=consensus.output_tokens,
        )

    # ── single agent path ────────────────────────────────
    if not primary_result.success or not primary_result.text.strip():
        logger.warning("Primary agent failed, no fallback available")
        return CoordinationResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
        )

    return CoordinationResult(
        text=primary_result.text,
        model=primary_result.model,
        input_tokens=primary_result.input_tokens,
        output_tokens=primary_result.output_tokens,
    )



# cognition/response_synthesizer.py

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)

# ─── TELEGRAM LIMITS ─────────────────────────────────────────────────────────

_TELEGRAM_MAX_CHARS = 4096

# ─── SUPPORTED LANGUAGES (hardcoded — covers ~95% of Telegram users) ─────────

_MESSAGES: dict[str, dict[str, str]] = {
    "insufficient_balance": {
        "en": "⚠️ *Insufficient balance.*\nPlease top up to continue.",
        "ru": "⚠️ *Недостаточно средств.*\nПополните баланс, чтобы продолжить.",
        "de": "⚠️ *Unzureichendes Guthaben.*\nBitte aufladen, um fortzufahren.",
        "fr": "⚠️ *Solde insuffisant.*\nVeuillez recharger pour continuer.",
        "es": "⚠️ *Saldo insuficiente.*\nPor favor recarga para continuar.",
        "pt": "⚠️ *Saldo insuficiente.*\nPor favor recarregue para continuar.",
        "it": "⚠️ *Saldo insufficiente.*\nRicarica per continuare.",
        "tr": "⚠️ *Yetersiz bakiye.*\nDevam etmek için lütfen bakiye yükleyin.",
        "ar": "⚠️ *رصيد غير كافٍ.*\nيرجى إعادة الشحن للمتابعة.",
        "zh": "⚠️ *余额不足。*\n请充值以继续。",
        "ja": "⚠️ *残高不足です。*\n続けるにはチャージしてください。",
        "ko": "⚠️ *잔액이 부족합니다.*\n계속하려면 충전해 주세요.",
        "pl": "⚠️ *Niewystarczające środki.*\nProszę doładować, aby kontynuować.",
        "uk": "⚠️ *Недостатньо коштів.*\nПоповніть баланс, щоб продовжити.",
        "fa": "⚠️ *موجودی کافی نیست.*\nلطفاً برای ادامه شارژ کنید.",
    },
    "no_response": {
        "en": "⚠️ No response received. Please try again.",
        "ru": "⚠️ Не удалось получить ответ. Попробуйте ещё раз.",
        "de": "⚠️ Keine Antwort erhalten. Bitte versuche es erneut.",
        "fr": "⚠️ Aucune réponse reçue. Veuillez réessayer.",
        "es": "⚠️ No se recibió respuesta. Por favor intenta de nuevo.",
        "pt": "⚠️ Nenhuma resposta recebida. Por favor tente novamente.",
        "it": "⚠️ Nessuna risposta ricevuta. Per favore riprova.",
        "tr": "⚠️ Yanıt alınamadı. Lütfen tekrar deneyin.",
        "ar": "⚠️ لم يتم تلقي أي رد. يرجى المحاولة مرة أخرى.",
        "zh": "⚠️ 未收到回复。请重试。",
        "ja": "⚠️ 返答がありませんでした。もう一度お試しください。",
        "ko": "⚠️ 응답을 받지 못했습니다. 다시 시도해 주세요.",
        "pl": "⚠️ Nie otrzymano odpowiedzi. Proszę spróbować ponownie.",
        "uk": "⚠️ Не вдалося отримати відповідь. Спробуйте ще раз.",
        "fa": "⚠️ پاسخی دریافت نشد. لطفاً دوباره امتحان کنید.",
    },
    "default_deny": {
        "en": "⚠️ Request cannot be processed.",
        "ru": "⚠️ Запрос не может быть выполнен.",
        "de": "⚠️ Anfrage kann nicht verarbeitet werden.",
        "fr": "⚠️ La demande ne peut pas être traitée.",
        "es": "⚠️ La solicitud no puede procesarse.",
        "pt": "⚠️ O pedido não pode ser processado.",
        "it": "⚠️ La richiesta non può essere elaborata.",
        "tr": "⚠️ İstek işlenemiyor.",
        "ar": "⚠️ لا يمكن معالجة الطلب.",
        "zh": "⚠️ 请求无法处理。",
        "ja": "⚠️ リクエストを処理できません。",
        "ko": "⚠️ 요청을 처리할 수 없습니다.",
        "pl": "⚠️ Żądanie nie może być przetworzone.",
        "uk": "⚠️ Запит не може бути виконаний.",
        "fa": "⚠️ درخواست قابل پردازش نیست.",
    },
    "truncation_suffix": {
        "en": "\n\n_...response truncated_",
        "ru": "\n\n_...ответ сокращён_",
        "de": "\n\n_...Antwort gekürzt_",
        "fr": "\n\n_...réponse tronquée_",
        "es": "\n\n_...respuesta truncada_",
        "pt": "\n\n_...resposta truncada_",
        "it": "\n\n_...risposta troncata_",
        "tr": "\n\n_...yanıt kısaltıldı_",
        "ar": "\n\n_...تم اقتصاص الرد_",
        "zh": "\n\n_...回复已截断_",
        "ja": "\n\n_...返答が省略されました_",
        "ko": "\n\n_...응답이 잘렸습니다_",
        "pl": "\n\n_...odpowiedź skrócona_",
        "uk": "\n\n_...відповідь скорочено_",
        "fa": "\n\n_...پاسخ کوتاه شد_",
    },
    "balance_display": {
        "en": "💰 Balance: $1.00",
        "ru": "💰 Баланс: $1.00",
        "de": "💰 Guthaben: $1.00",
        "fr": "💰 Solde : $1.00",
        "es": "💰 Saldo: $1.00",
        "pt": "💰 Saldo: $1.00",
        "it": "💰 Saldo: $1.00",
        "tr": "💰 Bakiye: $1.00",
        "ar": "💰 الرصيد: $1.00",
        "zh": "💰 余额：$1.00",
        "ja": "💰 残高：$1.00",
        "ko": "💰 잔액: $1.00",
        "pl": "💰 Saldo: $1.00",
        "uk": "💰 Баланс: $1.00",
        "fa": "💰 موجودی: $1.00",
    },
    "help_display": {
        "en": "ℹ️ Help",
        "ru": "ℹ️ Помощь",
        "de": "ℹ️ Hilfe",
        "fr": "ℹ️ Aide",
        "es": "ℹ️ Ayuda",
        "pt": "ℹ️ Ajuda",
        "it": "ℹ️ Aiuto",
        "tr": "ℹ️ Yardım",
        "ar": "ℹ️ مساعدة",
        "zh": "ℹ️ 帮助",
        "ja": "ℹ️ ヘルプ",
        "ko": "ℹ️ 도움말",
        "pl": "ℹ️ Pomoc",
        "uk": "ℹ️ Допомога",
        "fa": "ℹ️ راهنما",
    },
    "cancelled": {
        "en": "✅ Cancelled",
        "ru": "✅ Отменено",
        "de": "✅ Abgebrochen",
        "fr": "✅ Annulé",
        "es": "✅ Cancelado",
        "pt": "✅ Cancelado",
        "it": "✅ Annullato",
        "tr": "✅ İptal edildi",
        "ar": "✅ تم الإلغاء",
        "zh": "✅ 已取消",
        "ja": "✅ キャンセルしました",
        "ko": "✅ 취소됨",
        "pl": "✅ Anulowano",
        "uk": "✅ Скасовано",
        "fa": "✅ لغو شد",
    },
    "empty_message": {
        "en": "", "ru": "", "de": "", "fr": "", "es": "", "pt": "",
        "it": "", "tr": "", "ar": "", "zh": "", "ja": "", "ko": "",
        "pl": "", "uk": "", "fa": "",
    },
    "no_user_id": {
        "en": "", "ru": "", "de": "", "fr": "", "es": "", "pt": "",
        "it": "", "tr": "", "ar": "", "zh": "", "ja": "", "ko": "",
        "pl": "", "uk": "", "fa": "",
    },
}

_SILENT_KEYS = {"empty_message", "no_user_id"}


def get_system_message(key: str, lang: str) -> str:
    """
    Return localised system message.
    Falls back to English if lang not in registry.
    """
    bucket = _MESSAGES.get(key, {})
    return bucket.get(lang) or bucket.get("en", "")


# ─── I/O CONTRACTS ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SynthesisInput:
    raw_text: str
    intent: "Intent | None"   # ← было Intent, стало Optional
    tier: Tier
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"


@dataclass(frozen=True)
class SynthesisResult:
    text: str
    truncated: bool = False


# ─── INTERNAL HELPERS ────────────────────────────────────────────────────────

def _truncate(text: str, lang: str) -> tuple[str, bool]:
    suffix = get_system_message("truncation_suffix", lang)
    if len(text) <= _TELEGRAM_MAX_CHARS:
        return text, False
    cut = _TELEGRAM_MAX_CHARS - len(suffix)
    return text[:cut] + suffix, True


# ─── MAIN SYNTHESIZER ────────────────────────────────────────────────────────

def synthesize(inp: SynthesisInput) -> SynthesisResult:
    """
    Convert raw LLM output into final user-facing text.
    Pure function. No I/O. No state.
    """
    if inp.denied:
        if inp.deny_reason in _SILENT_KEYS:
            return SynthesisResult(text="")
        key = inp.deny_reason if inp.deny_reason in _MESSAGES else "default_deny"
        return SynthesisResult(text=get_system_message(key, inp.lang))

    if not inp.raw_text or not inp.raw_text.strip():
        return SynthesisResult(text=get_system_message("no_response", inp.lang))

    final, truncated = _truncate(inp.raw_text.strip(), inp.lang)
    return SynthesisResult(text=final, truncated=truncated)