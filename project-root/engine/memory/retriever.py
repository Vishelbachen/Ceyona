from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def get_project_memory(limit: int = 20):
    try:
        res = supabase.table("project_memory") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()

        return res.data or []

    except Exception as e:
        print("❌ PROJECT MEMORY READ ERROR:", e)
        return []