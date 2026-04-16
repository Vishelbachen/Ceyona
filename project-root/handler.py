from engine.llm import LLMEngine
from engine.memory.writer import save_memory

llm = LLMEngine()


async def handle_message(update, context):
    try:
        # =========================
        # 1. USER DATA
        # =========================
        user_message = update.message.text
        user_id = update.message.from_user.id

        if not user_message:
            return

        # =========================
        # 2. CALL LLM (WITH MEMORY)
        # =========================
        response = await llm.generate(
            text=user_message,
            user_id=str(user_id)
        )

        # =========================
        # 3. SEND RESPONSE
        # =========================
        await update.message.reply_text(response)

        # =========================
        # 4. SAVE MEMORY (IMPORTANT)
        # =========================
        try:
            save_memory(
                user_id=str(user_id),
                content=user_message,
                mem_type="user",
                importance=0.7
            )

            save_memory(
                user_id=str(user_id),
                content=response,
                mem_type="assistant",
                importance=0.8
            )

        except Exception as e:
            print("Memory save error:", e)

    except Exception as e:
        print("Handler error:", e)