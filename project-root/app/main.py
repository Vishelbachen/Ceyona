from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="v4.0 AI Execution System")

    # lazy imports (IMPORTANT FIX)
    from transport.telegram.webhook import router as telegram_router
    from security.rate_limiter import init_rate_limiter

    init_rate_limiter(app)
    app.include_router(telegram_router, prefix="/telegram")

    return app

app = create_app()


@app.get("/health")
def health():
    return {"status": "ok"}