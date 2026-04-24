from llm.groq_client import ask_groq

async def route_llm(agent_output: dict):

    prompt = str(agent_output)

    return await ask_groq(prompt)