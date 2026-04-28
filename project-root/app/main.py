from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from app.settings import get_settings
from app.bootstrap import get_container
from transport.telegram.webhook import router as telegram_router

# =========================
# INIT (single source)
# =========================
settings = get_settings()
container = get_container()

# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url=None,
)

# =========================
# ROUTES (IMPORT-TIME SAFE)
# =========================
app.include_router(telegram_router, prefix="/telegram")


# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.ENV,
    }


# =========================
# ENTRYPOINT
# =========================
def run():
    """
    Local/dev entrypoint.
    Production uses ASGI server.
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )


if __name__ == "__main__":
    run()