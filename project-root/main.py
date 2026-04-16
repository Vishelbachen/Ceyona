from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os
import sys

# 🔥 FIX: Railway-safe import path
sys.path.append(os.getcwd())

from engine.memory.writer import save_memory

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
    user_id = str(message.from_user.id)

    print("🔥 HANDLER ENTERED")
    print("USER MESSAGE:", text)
    print("USER ID:", user_id)

    if not llm:
        await message.answer("❌ LLM not available")
        return

    try:
        reply = await llm.generate(
            text,
            user_id=user_id
        )
    except Exception as e:
        reply = f"AI error: {e}"

    await message.answer(reply)

    # =========================
    # 💾 MEMORY SAVE (HARD SAFE VERSION)
    # =========================
    try:
        print("💾 SAVE MEMORY START")

        result1 = save_memory(
            user_id=user_id,
            content=text,
            mem_type="user",
            importance=0.7
        )

        print("💾 USER SAVED:", result1)

        result2 = save_memory(
            user_id=user_id,
            content=reply,
            mem_type="assistant",
            importance=0.8
        )

        print("💾 ASSISTANT SAVED:", result2)
        print("💾 SAVE MEMORY DONE")

    except Exception as e:
        print("❌ MEMORY SAVE FAILED:", e)


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