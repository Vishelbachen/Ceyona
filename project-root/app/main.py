from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap import bootstrap, shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ─────────────────────────────────────────
    state = await bootstrap()
    app.state.redis = state["redis"]
    app.state.supabase = state["supabase"]
    app.state.settings = state["settings"]

    yield

    # ── shutdown ─────────────────────────────────────────
    await shutdown(state)


app = FastAPI(
    title="AI Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,   # disable in production
    redoc_url=None,
)


@app.get("/health")
async def health():
    return {"status": "ok"}