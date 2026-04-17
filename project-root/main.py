from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os
import sys
import traceback

sys.path.append(os.getcwd())

from engine.memory.writer import save_memory

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = None
dp = Dispatcher()
llm = None


@app.on_event("startup")
async def startup():
    global bot, llm

    print("🔥 STARTING APP...")

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN IS MISSING")
    else:
        try:
            bot = Bot(token=BOT_TOKEN)
            print("✅ BOT INIT OK")
        except Exception as e:
            print("❌ BOT INIT ERROR:", e)
            traceback.print_exc()

    try:
        from engine.llm import LLMEngine
        llm = LLMEngine()
        print("✅ LLM INIT OK")
    except Exception as e:
        print("❌ LLM INIT ERROR:", e)
        traceback.print_exc()
        llm = None


@dp.message()
async def handle_message(message: types.Message):
    global llm

    text = message.text
    user_id = str(message.from_user.id)

    print("🔥 HANDLER ENTERED")
    print("USER MESSAGE:", text)
    print("USER ID:", user_id)

    if not llm:
        await message.answer("❌ LLM not available")
        return

    try:
        reply = await llm.generate(text, user_id=user_id)
    except Exception as e:
        print("❌ GENERATE ERROR:", e)
        traceback.print_exc()
        reply = f"AI error: {e}"

    await message.answer(reply)

    # =========================
    # MEMORY SAVE
    # =========================
    try:
        print("💾 SAVE MEMORY START")

        result1 = save_memory(user_id, text)
        print("💾 USER SAVED:", result1)

        result2 = save_memory(user_id, reply)
        print("💾 ASSISTANT SAVED:", result2)

        print("💾 SAVE MEMORY DONE")

    except Exception as e:
        print("❌ MEMORY SAVE FAILED:", e)
        traceback.print_exc()


@app.post("/webhook")
async def webhook(req: Request):
    global bot

    if not bot:
        return {"ok": False, "error": "bot not initialized"}

    data = await req.json()
    update = types.Update(**data)

    await dp.feed_update(bot, update)

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "alive"}