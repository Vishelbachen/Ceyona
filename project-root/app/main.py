from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.webhook import router as webhook_router


# -------------------------
# LIFESPAN (RAILWAY SAFE HOOK)
# -------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    print("AI Core System starting...")

    yield

    # shutdown
    print("AI Core System shutting down...")


# -------------------------
# APP INIT
# -------------------------
app = FastAPI(
    title="AI Core System",
    version="1.0.0",
    lifespan=lifespan
)


# -------------------------
# ROUTES
# -------------------------
app.include_router(webhook_router)


# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/")
async def health():
    return {"status": "ok"}