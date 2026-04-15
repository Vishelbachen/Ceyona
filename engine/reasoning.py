def build_prompt(message: str, memory: list):
    context = "\n".join(memory[-5:]) if memory else ""

    return f"""
You are a high-level AI assistant.

Context:
{context}

User:
{message}

Answer clearly, intelligently, without markdown artifacts or unnecessary formatting.
"""