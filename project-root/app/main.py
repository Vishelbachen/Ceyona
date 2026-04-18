from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI(
    title="AI Core System",
    version="1.0.0"
)


# Register routes
app.include_router(webhook_router)


@app.get("/")
async def health():
    return {
        "status": "ok",
        "system": "running"
    }