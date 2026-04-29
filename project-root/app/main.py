from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = await bootstrap()
    app.state.redis = state["redis"]
    app.state.supabase = state["supabase"]
    app.state.settings = state["settings"]
    app.state.access_controller = state["access_controller"]
    app.state.usage_meter = state["usage_meter"]

    # ── conversation history (Redis-backed) ──────────────
    from memory.conversation_history import ConversationHistory
    app.state.conversation_history = ConversationHistory(state["redis"])

    from transport.telegram.webhook import register_webhook
    await register_webhook()

    yield

    from app.bootstrap import shutdown
    await shutdown(state)


from app.bootstrap import bootstrap  # noqa: E402

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
async def health():
    return {"status": "ok"}