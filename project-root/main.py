import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

# 🔥 НОВОЕ — подключение Router
from engine.router import Router

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# =========================
# INIT
# =========================
app = FastAPI()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🔥 создаём Router
router = Router()


# =========================
# DEBUG STARTUP
# =========================
@app.on_event("startup")
async def on_startup():
    print("🔥 MAIN STARTED")
    print("🔍 BOT_TOKEN RAW:", repr(BOT_TOKEN))

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is missing")
        return

    if WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL)
            print(f"🔥 WEBHOOK SET: {WEBHOOK_URL}")
        except Exception as e:
            print("❌ WEBHOOK ERROR:", str(e))
    else:
        print("❌ WEBHOOK_URL is missing")


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()
    print("🛑 WEBHOOK DELETED")


# =========================
# AIogram HANDLER
# =========================
@dp.message()
async def handle_message(message):
    response = await router.handle(message.text)
    await message.answer(response)


# =========================
# WEBHOOK ENDPOINT
# =========================
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    print("📩 UPDATE RECEIVED")

    update = Update.model_validate(data)

    await dp.feed_update(bot, update)

    return {"ok": True}


# =========================
# HEALTH CHECK
# =========================
@app.get("/test")
async def test():
    return {"status": "alive"}