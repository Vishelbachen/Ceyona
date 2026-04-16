from supabase import create_client
import os
import time

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_memory(user_id: str, content: str, mem_type: str = "note", importance: float = 0.5):
    """
    Сохраняет память в Supabase
    """

    supabase.table("memory").insert({
        "user_id": str(user_id),
        "content": content,
        "type": mem_type,
        "importance": importance,
        "created_at": int(time.time())
    }).execute()