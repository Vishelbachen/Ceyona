# bootstrap.py
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="AI Execution System")

    # lazy imports (IMPORTANT)
    from transport.telegram.webhook import router as telegram_router

    app.include_router(telegram_router, prefix="/telegram")

    return app