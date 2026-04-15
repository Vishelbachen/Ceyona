import os
from supabase import create_client


class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        self.client = create_client(self.url, self.key)

    def insert(self, table: str, data: dict):
        return self.client.table(table).insert(data).execute()

    def select(self, table: str, filters: dict = None):
        query = self.client.table(table).select("*")

        if filters:
            for k, v in filters.items():
                query = query.eq(k, v)

        return query.execute()

    def update(self, table: str, filters: dict, data: dict):
        query = self.client.table(table).update(data)

        for k, v in filters.items():
            query = query.eq(k, v)

        return query.execute()