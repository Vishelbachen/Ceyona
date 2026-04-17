import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = None


# =========================
# INIT CLIENT
# =========================
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase retriever loaded")
    except Exception as e:
        print("❌ Supabase init error:", e)
else:
    print("⚠️ SUPABASE ENV MISSING")


# =========================
# GET MEMORY
# =========================
def get_memory(user_id: str, limit: int = 10):
    if not supabase:
        print("⚠️ SUPABASE NOT INITIALIZED")
        return []

    try:
        res = (
            supabase
            .table("memory")
            .select("*")
            .eq("user_id", str(user_id))
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )

        return res.data or []

    except Exception as e:
        print("❌ MEMORY RETRIEVE ERROR:", e)
        return []