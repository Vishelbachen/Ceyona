from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os
import sys
import traceback
import importlib

sys.path.append(os.getcwd())

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = None
dp = Dispatcher()
llm = None
save_memory = None


# =========================
# SAFE MEMORY IMPORT
# =========================
try:
    memory_writer = importlib.import_module("engine.memory.writer")
    save_memory = getattr(memory_writer, "save_memory", None)
    print("✅ Memory writer loaded")
except Exception as e:
    print("⚠️ Memory writer disabled:", e)
    save_memory = None


# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup():
    global bot, llm

    print("🔥 STARTING APP...")

    # BOT INIT
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN IS MISSING")
    else:
        try:
            bot = Bot(token=BOT_TOKEN)
            print("✅ BOT INIT OK")
        except Exception as e:
            print("❌ BOT INIT ERROR:", e)
            traceback.print_exc()

    # LLM INIT
    try:
        from engine.llm import LLMEngine
        llm = LLMEngine()
        print("✅ LLM INIT OK")
    except Exception as e:
        print("❌ LLM INIT ERROR:", e)
        traceback.print_exc()
        llm = None


# =========================
# MESSAGE HANDLER
# =========================
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

    # =========================
    # GENERATE
    # =========================
    try:
        reply = await llm.generate(text, user_id=user_id)
    except Exception as e:
        print("❌ GENERATE ERROR:", e)
        traceback.print_exc()
        reply = f"AI error: {e}"

    await message.answer(reply)

    # =========================
    # MEMORY SAVE (SAFE)
    # =========================
    if save_memory:
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
    else:
        print("⚠️ MEMORY DISABLED")


# =========================
# WEBHOOK
# =========================
@app.post("/webhook")
async def webhook(req: Request):
    global bot

    if not bot:
        return {"ok": False, "error": "bot not initialized"}

    try:
        data = await req.json()
        update = types.Update(**data)

        await dp.feed_update(bot, update)

        return {"ok": True}

    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        traceback.print_exc()
        return {"ok": False, "error": str(e)}


# =========================
# HEALTHCHECK
# =========================
@app.get("/")
async def root():
    return {"status": "alive"}