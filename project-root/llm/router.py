from llm.groq_client import ask_groq

async def route_llm(agent_output: dict):
    return await ask_groq(str(agent_output))