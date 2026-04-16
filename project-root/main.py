from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()

# ===== TELEGRAM HANDLER =====
@dp.message()
async def handle_message(message: types.Message):
    text = message.text

    # ТЕСТ GROQ (временный)
    if text.lower() == "force groq":
        try:
            from groq import Groq

            client = Groq(api_key=os.getenv("GROQ_API_KEY"))

            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "say ONLY GROQ_OK"}]
            )

            reply = "[GROQ] " + res.choices[0].message.content

        except Exception as e:
            reply = f"Groq error: {e}"

        await message.answer(reply)
        return

    # fallback
    await message.answer("Бот жив ✅")

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