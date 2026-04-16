from supabase import create_client
import os
import time

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def save_memory(user_id, content):
    supabase.table("memory").insert({
        "user_id": str(user_id),
        "content": content,
        "created_at": int(time.time())
    }).execute()