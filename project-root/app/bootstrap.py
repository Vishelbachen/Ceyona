from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="EPK System")

    # lazy import routers (CRITICAL FIX FOR RAILWAY)
    from transport.telegram.webhook import router as telegram_router
    from security.rate_limiter import init_rate_limiter

    init_rate_limiter(app)

    app.include_router(telegram_router, prefix="/telegram")

    return app