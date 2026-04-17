from datetime import datetime
from engine.memory.client import supabase


def save_memory(user_id: str, content: str, mem_type: str = "user", importance: float = 1.0):
    if not supabase:
        print("⚠️ SUPABASE NOT AVAILABLE")
        return "no_client"

    try:
        data = {
            "user_id": str(user_id),
            "content": content,
            "mem_type": mem_type,
            "importance": importance,
            "created_at": datetime.utcnow().isoformat()
        }

        res = supabase.table("memory").insert(data).execute()

        return res.data

    except Exception as e:
        print("❌ MEMORY WRITE ERROR:", e)
        return str(e)