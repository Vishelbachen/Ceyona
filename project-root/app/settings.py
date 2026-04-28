import os


class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    HF_TOKEN = os.getenv("HF_TOKEN")

    REDIS_URL = os.getenv("REDIS_URL")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    TON_WALLET = os.getenv("TON_WALLET")