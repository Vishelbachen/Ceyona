from fastapi import FastAPI
from app.api.webhook import router as webhook_router
from groq import Groq
import os

app = FastAPI()

app.include_router(webhook_router)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/models")
async def get_models():
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    models = client.models.list()

    return {
        "available_models": [m.id for m in models.data]
    }