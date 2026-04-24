from fastapi import FastAPI
from transport.telegram.webhook import router as telegram_router

def create_app() -> FastAPI:
    app = FastAPI(title="v4.0 AI System")

    app.include_router(telegram_router, prefix="/telegram")

    return app