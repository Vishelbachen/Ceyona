import os
from supabase import create_client


def _get_client():
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            print("⚠️ SUPABASE ENV MISSING")
            return None

        return create_client(url, key)

    except Exception as e:
        print("❌ SUPABASE INIT ERROR:", e)
        return None


def get_memory(user_id: str, limit: int = 5):
    try:
        client = _get_client()

        if not client:
            return []

        res = (
            client
            .table("memory")
            .select("content, created_at")
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        memories = [row["content"] for row in res.data]

        print(f"🧠 RETRIEVED MEMORY: {memories}")

        return memories

    except Exception as e:
        print("❌ MEMORY RETRIEVE ERROR:", e)
        return []