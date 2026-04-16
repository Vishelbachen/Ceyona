from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ===== SAFE INIT =====
bot = None
dp = Dispatcher()
llm = None


@app.on_event("startup")
async def startup():
    global bot, llm

    print("🔥 STARTING APP...")

    # ---- BOT SAFE INIT ----
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN IS MISSING")
    else:
        try:
            bot = Bot(token=BOT_TOKEN)
            print("✅ BOT INIT OK")
        except Exception as e:
            print("❌ BOT INIT ERROR:", e)

    # ---- LLM SAFE INIT ----
    try:
        from engine.llm import LLMEngine
        llm = LLMEngine()
        print("✅ LLM INIT OK")
    except Exception as e:
        print("❌ LLM INIT ERROR:", e)
        llm = None


# ===== HANDLER =====
@dp.message()
async def handle_message(message: types.Message):
    global llm

    text = message.text

    if not llm:
        await message.answer("❌ LLM not available")
        return

    try:
        reply = await llm.generate(text)
    except Exception as e:
        reply = f"AI error: {e}"

    await message.answer(reply)


# ===== WEBHOOK =====
@app.post("/webhook")
async def webhook(req: Request):
    global bot

    if not bot:
        return {"ok": False, "error": "bot not initialized"}

    data = await req.json()
    update = types.Update(**data)

    await dp.feed_update(bot, update)

    return {"ok": True}


# ===== HEALTH =====
@app.get("/")
async def root():
    return {"status": "alive"}