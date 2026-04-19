import os


class Settings:
    """
    Production-safe configuration loader.
    """

    def __init__(self):
        # 🔐 AI / LLM
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")

        # 🤖 Telegram (CRITICAL)
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        # 🔐 Security
        self.JWT_SECRET = os.getenv("JWT_SECRET")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

        # 🗄 DB (future)
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # 🌐 APIs
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
        self.SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        self.BREVO_API_KEY = os.getenv("BREVO_API_KEY")

        # 💳 future
        self.TON_WALLET = os.getenv("TON_WALLET")

        # 🚀 deployment
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL")

        # 🧯 validate AFTER loading
        self._validate()

    def _validate(self):
        missing = []

        # critical only (НЕ ломаем систему лишним)
        if not self.BOT_TOKEN:
            missing.append("BOT_TOKEN")

        if missing:
            raise RuntimeError(
                f"[CONFIG ERROR] Missing env vars: {', '.join(missing)}"
            )


# singleton
settings = Settings()