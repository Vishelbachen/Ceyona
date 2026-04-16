from engine.memory.writer import save_memory

# user message
user_message = update.message.text
user_id = update.message.from_user.id

# after LLM response
response = await llm.generate(user_message, user_id=user_id)

# SAVE MEMORY (обязательно)
save_memory(user_id, user_message, "user", 0.7)
save_memory(user_id, response, "assistant", 0.8)