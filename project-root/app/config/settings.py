import os


class Settings:
    """
    Centralized application configuration.
    Loads all environment variables in one place.
    """

    def __init__(self):
        # 🔐 AI / LLM
        self.GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

        # 🤖 Telegram
        self.BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")

        # 🔐 Security
        self.JWT_SECRET: str | None = os.getenv("JWT_SECRET")
        self.ENCRYPTION_KEY: str | None = os.getenv("ENCRYPTION_KEY")

        # 🗄 Database (reserved for future)
        self.SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY: str | None = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # 🌐 External APIs
        self.OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN: str | None = os.getenv("MAPBOX_TOKEN")
        self.SERPAPI_KEY: str | None = os.getenv("SERPAPI_KEY")
        self.BREVO_API_KEY: str | None = os.getenv("BREVO_API_KEY")

        # 💳 Payments (future)
        self.TON_WALLET: str | None = os.getenv("TON_WALLET")

        # 🚀 Deployment
        self.WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL")

        # ✅ FAIL-FAST CHECK
        self._validate()

    def _validate(self):
        """
        Ensures critical variables exist.
        Fails early instead of breaking at runtime.
        """

        missing = []

        if not self.BOT_TOKEN:
            missing.append("BOT_TOKEN")

        # 👉 пока GROQ optional (у тебя fake LLM)
        # if not self.GROQ_API_KEY:
        #     missing.append("GROQ_API_KEY")

        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


# Singleton instance (used across the app)
settings = Settings()