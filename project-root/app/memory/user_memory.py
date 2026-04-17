from engine.memory.client import get_client


def save_memory(user_id: str, content: str, mem_type: str = "chat", importance: float = 1.0):
    try:
        client = get_client()

        return client.table("memory").insert({
            "user_id": user_id,
            "content": content,
            "mem_type": mem_type,
            "importance": importance
        }).execute().data

    except Exception as e:
        print("Memory write error:", e)
        return None


def get_memory(user_id: str, limit: int = 10):
    try:
        client = get_client()

        res = (
            client.table("memory")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return res.data or []

    except Exception as e:
        print("Memory retrieve error:", e)
        return []