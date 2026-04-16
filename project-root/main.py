import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from engine.router import Router

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

router = Router()


@app.on_event("startup")
async def startup():
    print("🔥 AI SYSTEM STARTED")

    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"🔥 WEBHOOK SET: {WEBHOOK_URL}")


@dp.message()
async def handle(message):
    response = await router.handle(message.text)
    await message.answer(response)


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/test")
async def test():
    return {"status": "alive"}