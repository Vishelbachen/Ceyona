from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os

from engine.llm import LLMEngine

# ===== INIT =====
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()

llm = LLMEngine()

# ===== TELEGRAM HANDLER =====
@dp.message()
async def handle_message(message: types.Message):
    text = message.text

    try:
        reply = await llm.generate(text)
    except Exception as e:
        reply = f"AI error: {e}"

    await message.answer(reply)

# ===== WEBHOOK =====
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}

# ===== HEALTH =====
@app.get("/")
async def root():
    return {"status": "alive"}