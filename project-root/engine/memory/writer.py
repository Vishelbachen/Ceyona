import os
from supabase import create_client, Client


def _get_client() -> Client | None:
    try:
        url = os.getenv("SUPABASE_URL")

        # поддержка двух вариантов ключей
        key = (
            os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        )

        if not url or not key:
            print("⚠️ SUPABASE ENV MISSING")
            return None

        return create_client(url, key)

    except Exception as e:
        print("❌ SUPABASE INIT ERROR:", e)
        return None


def save_memory(user_id: str, content: str):
    try:
        client = _get_client()

        if not client:
            return "no_client"

        data = {
            "user_id": str(user_id),
            "content": content,
            "importance": 1.0
        }

        res = client.table("memory").insert(data).execute()

        return res.data

    except Exception as e:
        print("❌ SAVE MEMORY ERROR:", e)
        return "error"