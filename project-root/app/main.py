from fastapi import FastAPI

from app.bootstrap import get_container
from app.settings import settings

from transport.telegram.webhook import router as telegram_router


# =========================
# 🚀 APP INIT
# =========================
app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
)


# =========================
# 🧩 BOOTSTRAP SYSTEM
# =========================
container = get_container()


# =========================
# 🌐 ROUTES (TRANSPORT LAYER ONLY)
# =========================
app.include_router(telegram_router)


# =========================
# ❤️ HEALTHCHECK
# =========================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-platform",
    }


# =========================
# 🧠 LIFECYCLE HOOKS (OPTIONAL SAFE INIT)
# =========================
@app.on_event("startup")
async def startup_event():
    """
    Only safe initialization.
    No business logic.
    """
    container.logger.info("System starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup only.
    """
    container.logger.info("System shutting down")