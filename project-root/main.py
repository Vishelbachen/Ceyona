import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

# ======================
# ENV
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ======================
# INIT
# ======================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()


# ======================
# ROUTER (пока минимальный слой)
# ======================
async def process_message(text: str) -> str:
    text = (text or "").lower()

    if "привет" in text:
        return "Привет 👋 Бот работает"
    if "как дела" in text:
        return "Всё стабильно 🚀"

    return f"Я получил: {text}"


# ======================
# HANDLER
# ======================
@dp.message()
async def handle_message(message):
    response = await process_message(message.text)
    await message.answer(response)


# ======================
# WEBHOOK ENDPOINT
# ======================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.model_validate(data)  # 🔥 ВАЖНО (совместимо с aiogram v3)

    await dp.feed_update(bot, update)
    return {"ok": True}


# ======================
# TEST ENDPOINT (ОЧЕНЬ ВАЖНО ДЛЯ ДИАГНОСТИКИ)
# ======================
@app.get("/test")
async def test():
    return {"status": "ok", "service": "alive"}


# ======================
# STARTUP
# ======================
@app.on_event("startup")
async def on_startup():
    print("🔥 MAIN STARTED")

    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"🔥 Webhook set: {WEBHOOK_URL}")
    else:
        print("❌ WEBHOOK_URL missing")


# ======================
# SHUTDOWN
# ======================
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()