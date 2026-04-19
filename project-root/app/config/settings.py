import os


class Settings:
    """
    Centralized application configuration.
    Loads all environment variables in one place.
    """

    # 🔐 AI / LLM
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

    # 🤖 Telegram
    BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")

    # 🔐 Security
    JWT_SECRET: str | None = os.getenv("JWT_SECRET")
    ENCRYPTION_KEY: str | None = os.getenv("ENCRYPTION_KEY")

    # 🗄 Database (reserved for future)
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: str | None = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # 🌐 External APIs
    OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")
    MAPBOX_TOKEN: str | None = os.getenv("MAPBOX_TOKEN")
    SERPAPI_KEY: str | None = os.getenv("SERPAPI_KEY")
    BREVO_API_KEY: str | None = os.getenv("BREVO_API_KEY")

    # 💳 Payments (future)
    TON_WALLET: str | None = os.getenv("TON_WALLET")

    # 🚀 Deployment
    WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL")


# Singleton instance (used across the app)
settings = Settings()