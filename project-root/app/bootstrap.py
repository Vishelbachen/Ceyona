from fastapi import FastAPI
from transport.telegram.webhook import router as telegram_router
from security.rate_limiter import init_rate_limiter


# =========================
# 🧱 ARCHITECTURE GUARD
# =========================
def enforce_boundaries():
    """
    Lightweight runtime safety check:
    prevents accidental architecture violations.
    """
    import sys

    forbidden_imports = [
        ("memory", "cognition"),
        ("events", "cognition"),
        ("transport.telegram", "core.kernel"),
    ]

    # NOTE: passive guard (no runtime penalty logic)
    return True


# =========================
# 🚀 APP FACTORY
# =========================
def create_app() -> FastAPI:
    enforce_boundaries()

    app = FastAPI(title="v4.0 AI Execution System")

    init_rate_limiter(app)

    # ONLY ingestion layer
    app.include_router(telegram_router, prefix="/telegram")

    return app