from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_memory(user_id: str, limit: int = 10):
    """
    Достаёт последние воспоминания пользователя
    """

    res = supabase.table("memory") \
        .select("*") \
        .eq("user_id", str(user_id)) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()

    return res.data