import os
from supabase import create_client, Client

_supabase = None


def get_client() -> Client:
    global _supabase

    if _supabase:
        return _supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise Exception("SUPABASE ENV MISSING")

    _supabase = create_client(url, key)
    return _supabase