from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap import bootstrap, shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────
    state = await bootstrap()
    app.state.redis = state["redis"]
    app.state.supabase = state["supabase"]
    app.state.settings = state["settings"]

    # register webhook with Telegram
    from transport.telegram.webhook import register_webhook
    await register_webhook()

    yield

    # ── shutdown ─────────────────────────────────────────
    await shutdown(state)


app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

# ─── ROUTERS ─────────────────────────────────────────────────────────────────

from transport.telegram.webhook import router as telegram_router  # noqa: E402
app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"status": "ok"}