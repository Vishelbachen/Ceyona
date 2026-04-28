class SupabaseStore:
    """
    External persistent storage abstraction (mock)
    """

    def save(self, key: str, value: dict):
        print(f"[SUPABASE] save {key}")

    def load(self, key: str):
        print(f"[SUPABASE] load {key}")
        return {}