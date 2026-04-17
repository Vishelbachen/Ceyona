from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


def save_project_memory(file: str, action: str, content: str):
    try:
        res = supabase.table("project_memory").insert({
            "file": file,
            "action": action,
            "content": content
        }).execute()

        print("📦 PROJECT MEMORY SAVED:", res.data)
        return res.data

    except Exception as e:
        print("❌ PROJECT MEMORY ERROR:", e)
        return None