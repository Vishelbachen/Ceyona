from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.settings import get_settings
from app.bootstrap import get_container

# =========================
# FASTAPI APP INIT
# =========================
app = FastAPI(
    title="AI Platform",
    version="4.7",
    docs_url="/docs",
    redoc_url=None,
)

# =========================
# GLOBALS (LAZY SAFE)
# =========================
settings = None
container = None


# =========================
# LIFECYCLE EVENTS (CLEAN v4.7 WAY)
# =========================
@app.on_event("startup")
def startup():
    """
    Controlled DI initialization (Railway-safe).
    """
    global settings, container

    settings = get_settings()
    container = get_container()

    # transport layer registration (safe after DI init)
    from transport.telegram.webhook import router as telegram_router
    app.include_router(telegram_router, prefix="/telegram")


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME if settings else "AI Platform",
        "version": settings.APP_VERSION if settings else "4.7",
        "env": settings.ENV if settings else "unknown",
    }


# =========================
# ENTRYPOINT
# =========================
def run():
    """
    Local/dev entrypoint.
    Production uses ASGI server (Railway/Docker).
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(settings.DEBUG if settings else False),
    )


if __name__ == "__main__":
    run()