from fastapi import FastAPI
from groq import Groq
import os

app = FastAPI()


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