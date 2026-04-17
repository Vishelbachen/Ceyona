from engine.memory.user_memory import get_memory as get_user_memory


def build_memory_context(user_id: str):
    memory = get_user_memory(user_id, limit=10)

    lines = []
    for m in memory:
        content = m.get("content")
        if content:
            lines.append(content)

    return "\n".join(lines)