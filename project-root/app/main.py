from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI()

app.include_router(webhook_router)


@app.get("/")
async def health():
    return {"status": "ok"}