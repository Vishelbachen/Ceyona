import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):

        # ======================
        # ENV MODE
        # ======================
        self.ENV = self._get("ENV", "production")  # production / dev
        self.DEBUG = self._bool("DEBUG", False)

        # ======================
        # BOT CORE
        # ======================
        self.BOT_TOKEN = self._get("BOT_TOKEN")

        # webhook (NEW - needed for Railway production mode)
        self.WEBHOOK_URL = self._get("WEBHOOK_URL", "")

        # ======================
        # AI MODELS
        # ======================
        self.GEMINI_API_KEY = self._get("GEMINI_API_KEY")
        self.OPENAI_API_KEY = self._get("OPENAI_API_KEY")
        self.GROQ_API_KEY = self._get("GROQ_API_KEY")
        self.MISTRAL_API_KEY = self._get("MISTRAL_API_KEY")

        # ======================
        # MEMORY (SUPABASE)
        # ======================
        self.SUPABASE_URL = self._get("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = self._get("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = self._get("SUPABASE_SERVICE_ROLE_KEY")

        # ======================
        # SEARCH / TOOLS
        # ======================
        self.SERPAPI_KEY = self._get("SERPAPI_KEY")
        self.OPENWEATHER_API_KEY = self._get("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = self._get("MAPBOX_TOKEN")
        self.GOOGLE_MAPS_API_KEY = self._get("GOOGLE_MAPS_API_KEY")

        # ======================
        # PAYMENTS
        # ======================
        self.TON_WALLET = self._get("TON_WALLET", "")

        # ======================
        # SECURITY
        # ======================
        self.JWT_SECRET = self._get("JWT_SECRET")
        self.ENCRYPTION_KEY = self._get("ENCRYPTION_KEY")

        # ======================
        # PERFORMANCE SETTINGS
        # ======================
        self.REQUEST_TIMEOUT = int(self._get("REQUEST_TIMEOUT", 45))
        self.MAX_RETRIES = int(self._get("MAX_RETRIES", 2))

        # ======================
        # MEMORY FLAGS
        # ======================
        self.MEMORY_ENABLED = self._bool("MEMORY_ENABLED", True)

        # ======================
        # VALIDATION
        # ======================
        self._validate()

    # =========================
    # HELPERS
    # =========================
    def _get(self, key: str, default: str = None):
        value = os.getenv(key, default)
        if value is not None:
            value = str(value).strip()
        return value

    def _bool(self, key: str, default: bool = False):
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    # =========================
    # VALIDATION (SAFE MODE)
    # =========================
    def _validate(self):

        required = {
            "BOT_TOKEN": self.BOT_TOKEN,
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": self.SUPABASE_SERVICE_ROLE_KEY,
            "JWT_SECRET": self.JWT_SECRET,
            "ENCRYPTION_KEY": self.ENCRYPTION_KEY,
        }

        missing = [k for k, v in required.items() if not v]

        if missing:
            raise ValueError(
                "❌ Missing critical env vars: "
                + ", ".join(missing)
            )

        # webhook safety check
        if self.WEBHOOK_URL == "" and self.ENV == "production":
            print(
                "⚠️ WARNING: WEBHOOK_URL is empty. "
                "Bot may not receive updates in production."
            )