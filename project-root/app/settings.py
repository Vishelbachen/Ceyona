import os

class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    REDIS_URL = os.getenv("REDIS_URL")
    SENTRY_DSN = os.getenv("SENTRY_DSN")
    TON_WALLET = os.getenv("TON_WALLET")

settings = Settings()