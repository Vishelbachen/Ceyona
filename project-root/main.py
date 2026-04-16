from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
import os

from engine.memory.writer import save_memory  # ✅ ДОБАВЛЕНО

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

    print("USER MESSAGE:", text)
    print("USER ID:", user_id)

    if not llm:
        await message.answer("❌ LLM not available")
        return

    try:
        # =========================
        # LLM CALL (WITH MEMORY READ)
        # =========================
        reply = await llm.generate(
            text,
            user_id=user_id
        )

    except Exception as e:
        reply = f"AI error: {e}"

    await message.answer(reply)

    # =========================
    # 💾 MEMORY SAVE (CRITICAL FIX)
    # =========================
    try:
        save_memory(
            user_id=user_id,
            content=text,
            mem_type="user",
            importance=0.7
        )

        save_memory(
            user_id=user_id,
            content=reply,
            mem_type="assistant",
            importance=0.8
        )

    except Exception as e:
        print("Memory save error:", e)


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