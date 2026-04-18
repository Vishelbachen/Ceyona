from fastapi import FastAPI
from app.bot import router as bot_router

app = FastAPI()

app.include_router(bot_router)


@app.get("/")
async def health():
    return {"status": "ok"}