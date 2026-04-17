import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase writer loaded")
    except Exception as e:
        print("❌ Supabase init error:", e)
else:
    print("⚠️ SUPABASE ENV MISSING")


def save_memory(user_id: str, content: str, mem_type: str = None, importance: float = 1.0):
    if not supabase:
        print("⚠️ SUPABASE NOT INITIALIZED")
        return None

    try:
        data = {
            "user_id": str(user_id),
            "content": content,
            "mem_type": mem_type,
            "importance": importance,
        }

        result = supabase.table("memory").insert(data).execute()
        return result.data

    except Exception as e:
        print("❌ Memory write error:", e)
        return None