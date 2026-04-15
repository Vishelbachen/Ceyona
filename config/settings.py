import os


class Settings:
    """
    Runtime configuration loader (Railway-ready)
    """

    # =========================
    # CORE TOKENS
    # =========================
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    JWT_SECRET = os.getenv("JWT_SECRET")

    # =========================
    # AI PROVIDERS
    # =========================
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

    # =========================
    # SERVICES
    # =========================
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    # =========================
    # DATABASE
    # =========================
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # =========================
    # PAYMENT (TON)
    # =========================
    TON_WALLET = os.getenv("TON_WALLET")

    # =========================
    # DEPLOYMENT
    # =========================
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

    # =========================
    # MODE FLAGS
    # =========================
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    FAST_MODE = os.getenv("FAST_MODE", "false").lower() == "true"