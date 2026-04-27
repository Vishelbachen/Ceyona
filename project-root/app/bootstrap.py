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
@dataclass
class Container:
    settings = get_settings()

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

    # SECURITY
    auth = AuthService(settings=settings)

    encryption = EncryptionService(settings=settings)

    rate_limiter = RateLimiter(
        max_requests_per_window=60,
        window_seconds=60,
    )

    # ❗ FIX: OriginGuard требует settings
    origin_guard = OriginGuard(settings=settings)

    # PAYMENTS
    pricing_engine = PricingEngine()
    access_controller = AccessController()
    usage_meter = UsageMeter()

    from payments.ton_client import TONClient

    ton_client = TONClient(api_key=settings.TON_WALLET)

    wallet_manager = WalletManager(ton_client=ton_client)

    # LLM
    model_router = ModelRouter(
        groq_key=settings.GROQ_API_KEY,
        hf_token=settings.HF_TOKEN,
    )

    # CORE
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
# SINGLETON
# =========================
_container: Container | None = None


def get_container() -> Container:
    global _container

    if _container is None:
        _container = build_container()

    return _container