from __future__ import annotations

from dataclasses import dataclass

from app.settings import get_settings

from security.auth import AuthService
from security.encryption import EncryptionService
from security.rate_limiter import RateLimiter
from security.origin_guard import OriginGuard

from payments.access_controller import AccessController
from payments.pricing_engine import PricingEngine
from payments.usage_meter import UsageMeter
from payments.wallet_manager import WalletManager

from llm.model_router import ModelRouter

from core.execution.orchestrator import Orchestrator


# =========================
# DI CONTAINER (LIGHTWEIGHT)
# =========================
@dataclass
class Container:
    """
    Central dependency container.

    ROLE:
    - instantiate core system components
    - manage dependency wiring
    - provide single source of runtime graph

    DOES NOT:
    - contain logic
    - execute workflows
    - make decisions
    """

    settings = get_settings()

    # =========================
    # SECURITY LAYER
    # =========================
    auth: AuthService
    encryption: EncryptionService
    rate_limiter: RateLimiter
    origin_guard: OriginGuard

    # =========================
    # PAYMENTS LAYER
    # =========================
    access_controller: AccessController
    pricing_engine: PricingEngine
    usage_meter: UsageMeter
    wallet_manager: WalletManager

    # =========================
    # LLM LAYER
    # =========================
    model_router: ModelRouter

    # =========================
    # EXECUTION CORE
    # =========================
    orchestrator: Orchestrator


# =========================
# BOOTSTRAP FUNCTION
# =========================
def build_container() -> Container:
    """
    Creates fully wired application graph.

    ORDER IS IMPORTANT (dependency-safe construction).
    """

    settings = get_settings()

    # =========================
    # SECURITY
    # =========================
    auth = AuthService(
        settings=settings  # ← ЕДИНСТВЕННОЕ ИСПРАВЛЕНИЕ
    )

    encryption = EncryptionService()

    rate_limiter = RateLimiter(
        max_requests_per_minute=60,
        window_seconds=60,
    )

    origin_guard = OriginGuard()

    # =========================
    # PAYMENTS
    # =========================
    pricing_engine = PricingEngine()

    access_controller = AccessController()

    usage_meter = UsageMeter()

    # TON client is assumed to exist in your architecture
    from payments.ton_client import TONClient

    ton_client = TONClient(
        api_key=settings.TON_WALLET
    )

    wallet_manager = WalletManager(
        ton_client=ton_client
    )

    # =========================
    # LLM
    # =========================
    model_router = ModelRouter(
        groq_key=settings.GROQ_API_KEY,
        hf_token=settings.HF_TOKEN,
    )

    # =========================
    # CORE ORCHESTRATION
    # =========================
    orchestrator = Orchestrator(
        auth=auth,
        rate_limiter=rate_limiter,
        origin_guard=origin_guard,
        access_controller=access_controller,
        pricing_engine=pricing_engine,
        usage_meter=usage_meter,
        model_router=model_router,
    )

    return Container(
        auth=auth,
        encryption=encryption,
        rate_limiter=rate_limiter,
        origin_guard=origin_guard,
        access_controller=access_controller,
        pricing_engine=pricing_engine,
        usage_meter=usage_meter,
        wallet_manager=wallet_manager,
        model_router=model_router,
        orchestrator=orchestrator,
    )


# =========================
# GLOBAL SINGLETON (OPTIONAL)
# =========================
_container: Container | None = None


def get_container() -> Container:
    """
    Lazy singleton container.

    Safe for FastAPI / Telegram webhook runtime.
    """
    global _container

    if _container is None:
        _container = build_container()

    return _container