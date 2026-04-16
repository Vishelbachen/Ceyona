from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

def get_memory(user_id: str, limit: int = 10):
    try:
        res = supabase.table("memory") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return res.data or []
    except Exception as e:
        print("Memory read error:", e)
        return []