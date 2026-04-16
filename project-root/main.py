import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()


# --- SIMPLE ROUTER ---
async def router(text: str) -> str:
    text = (text or "").lower()

    if "привет" in text:
        return "Привет 👋 система снова онлайн"
    if "как дела" in text:
        return "Работаю стабильно 🚀"

    return f"Эхо: {text}"


# --- HANDLER ---
@dp.message()
async def handle_message(message):
    response = await router(message.text)
    await message.answer(response)


# --- WEBHOOK ---
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


# --- STARTUP ---
@app.on_event("startup")
async def startup():
    print("🔥 BOT STARTED")

    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print("🔥 WEBHOOK SET")