from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.bootstrap import bootstrap, shutdown
from infra.env_validator import validate
from observability.logger import setup_logging
from observability.sentry import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    validate()
    init_sentry()

    state = await bootstrap()
    app.state.redis = state["redis"]
    app.state.supabase = state["supabase"]
    app.state.settings = state["settings"]

    # init rate limiter
    from security.rate_limiter import init_rate_limiter
    init_rate_limiter(state["redis"])

    # register webhook
    from transport.telegram.webhook import register_webhook
    await register_webhook()

    yield

    await shutdown(state)


app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

from transport.telegram.webhook import router as telegram_router  # noqa: E402
app.include_router(telegram_router)


@app.get("/health")
async def health(request: Request):
    from infra.healthcheck import full_health
    result = await full_health(request.app.state.redis, request.app.state.supabase)
    return result