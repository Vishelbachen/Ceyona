from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_memory(user_id):
    res = supabase.table("memory") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()

    return res.data or []