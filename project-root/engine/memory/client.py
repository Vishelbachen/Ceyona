import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")  # фиксируем единый стандарт

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ SUPABASE ENV MISSING")

supabase = None

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client initialized")
except Exception as e:
    print("❌ Supabase init failed:", e)
    supabase = None