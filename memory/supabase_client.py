from supabase import create_client, Client


class SupabaseClient:
    def __init__(self, settings):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_SERVICE_ROLE_KEY

        self.client: Client = create_client(self.url, self.key)

    def insert(self, table: str, data: dict):
        return self.client.table(table).insert(data).execute()

    def select(self, table: str, filters: dict = None, limit: int = 10):
        query = self.client.table(table).select("*")

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        return query.limit(limit).execute()

    def rpc(self, fn: str, params: dict):
        return self.client.rpc(fn, params).execute()