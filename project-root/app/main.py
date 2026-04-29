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
    await regist