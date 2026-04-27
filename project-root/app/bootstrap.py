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
# DI CONTAINER
# =========================
@dataclass(frozen=True)
class Container:
    auth: AuthService
    encryption: EncryptionService
    rate_limiter: RateLimiter
    origin_guard: OriginGuard

    access_controller: AccessController
    pricing_engine: PricingEngine
    usage_meter: UsageMeter
    wallet_manager: WalletManager

    model_router: ModelRouter
    orchestrator: Orchestrator


# =========================
# BOOTSTRAP
# =========================
def build_container() -> Container:
    settings = get_settings()

    # =========================
    # SECURITY LAYER
    # =========================
    auth = AuthService(settings=settings)

    encryption = EncryptionService(settings=settings)

    rate_limiter = RateLimiter(
        max_requests_per_window=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
    )

    origin_guard = OriginGuard(settings=settings)

    # =========================
    # PAYMENTS LAYER
    # =========================
    pricing_engine = PricingEngine()

    access_controller = AccessController()

    usage_meter = UsageMeter()

    from payments.ton_client import TONClient

    ton_client = TONClient(
        api_key=settings.TON_WALLET
    )

    wallet_manager = WalletManager(
        ton_client=ton_client
    )

    # =========================
    # LLM LAYER
    # =========================
    model_router = ModelRouter(
        groq_key=settings.GROQ_API_KEY,
        hf_token=settings.HF_TOKEN,
    )

    # =========================
    # EXECUTION CORE
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
# SINGLETON (RUNTIME SAFE)
# =========================
_container: Container | None = None


def get_container() -> Container:
    global _container

    if _container is None:
        _container = build_container()

    return _container