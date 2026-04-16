from supabase import create_client
import os
import time

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # ВАЖНО
)

def save_memory(user_id: str, content: str, mem_type: str = "note", importance: float = 0.5):
    try:
        supabase.table("memory").insert({
            "user_id": str(user_id),
            "content": content,
            "type": mem_type,
            "importance": importance,
            "created_at": int(time.time())
        }).execute()
    except Exception as e:
        print("Memory write error:", e)