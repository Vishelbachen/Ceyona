from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

def save_memory(user_id: str, content: str):
    try:
        res = supabase.table("memory").insert({
            "user_id": str(user_id),
            "content": content
        }).execute()

        return res.data

    except Exception as e:
        print("Memory write error:", e)
        return None