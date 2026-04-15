from engine.router import route_model
from engine.memory import retrieve_memory, store_memory
from engine.reasoning import build_prompt
from engine.selfcorrection import refine_output

async def process_request(user_id: str, message: str):
    memory = await retrieve_memory(user_id)

    prompt = build_prompt(message, memory)

    model = route_model(message)

    raw_output = await model.generate(prompt)

    improved = refine_output(raw_output)

    await store_memory(user_id, message, improved)

    return improved