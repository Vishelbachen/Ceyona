from supabase import create_client
from app.settings import settings

class SupabaseStore:

    def __init__(self):
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def write_event(self, table: str, data: dict):
        return self.client.table(table).insert(data).execute()

    def read(self, table: str, query: dict):
        return self.client.table(table).select("*").match(query).execute()