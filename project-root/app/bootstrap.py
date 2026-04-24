from fastapi import FastAPI
from transport.telegram.webhook import router as telegram_router
from security.rate_limiter import init_rate_limiter
from memory.supabase_store import SupabaseStore

def create_app() -> FastAPI:
    app = FastAPI(title="v4.0 AI Execution System")

    init_rate_limiter(app)

    app.include_router(telegram_router, prefix="/telegram")

    return app