import os


class Settings:
    """
    Production-safe configuration loader.
    Single source of truth for all environment variables.
    """

    def __init__(self):
        # 🔐 AI / LLM (CRITICAL)
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

        # 🧠 MODEL GROUPS (centralized routing config)
        self.FAST_MODELS = [
            "groq/compound-mini",
            "llama-3.1-8b-instant",
        ]

        self.GENERAL_MODELS = [
            "llama-3.3-70b-versatile",
            "qwen/qwen3-32b",
            "openai/gpt-oss-20b",
        ]

        self.HEAVY_MODELS = [
            "openai/gpt-oss-120b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]

        self.SAFETY_MODELS = [
            "openai/gpt-oss-safeguard-20b",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
        ]

        self.AUDIO_MODELS = [
            "whisper-large-v3",
            "whisper-large-v3-turbo",
        ]

        self.EXPERIMENTAL_MODELS = [
            "allam-2-7b",
            "groq/compound",
            "canopylabs/orpheus-v1-english",
            "canopylabs/orpheus-arabic-saudi",
        ]

        # 🧯 validate AFTER loading
        self._validate()

    def _validate(self):
        missing = []

        # critical dependencies
        if not self.BOT_TOKEN:
            missing.append("BOT_TOKEN")

        # 🔥 FIX: теперь LLM тоже fail-fast (важно для прода)
        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")

        # safety check for routing stability
        if not self.FAST_MODELS:
            missing.append("FAST_MODELS")

        if not self.GENERAL_MODELS:
            missing.append("GENERAL_MODELS")

        if missing:
            raise RuntimeError(
                f"[CONFIG ERROR] Missing env vars: {', '.join(missing)}"
            )


# singleton (global access point)
settings = Settings()