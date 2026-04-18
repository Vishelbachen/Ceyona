import os
from supabase import create_client


class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client = create_client(self.url, self.key)

    async def save_message(self, user_id: str, role: str, content: str):
        try:
            self.client.table("messages").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()
        except:
            pass

    async def get_history(self, user_id: str, limit: int = 10):
        try:
            res = self.client.table("messages") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()

            return list(reversed(res.data))

        except:
            return []