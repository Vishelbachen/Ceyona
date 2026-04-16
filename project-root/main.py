import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

# ======================
# ENV VARIABLES
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
# BASIC HANDLER
# ======================
@dp.message()
async def handle_message(message):
    await message.answer("Бот работает 🚀")

# ======================
# WEBHOOK ENDPOINT
# ======================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}

# ======================
# STARTUP
# ======================
@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        print(f"Webhook set to {WEBHOOK_URL}")
    else:
        print("WEBHOOK_URL not set!")

# ======================
# SHUTDOWN
# ======================
@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()