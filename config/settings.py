import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):

        # ======================
        # ENV MODE
        # ======================
        self.ENV = self._get("ENV", "production")
        self.DEBUG = self._bool("DEBUG", False)

        # ======================
        # BOT CORE
        # ======================
        self.BOT_TOKEN = self._get("BOT_TOKEN")
        self.WEBHOOK_URL = self._get("WEBHOOK_URL", "").rstrip("/")

        # ======================
        # AI MODELS
        # ======================
        self.GEMINI_API_KEY = self._get("GEMINI_API_KEY")
        self.OPENAI_API_KEY = self._get("OPENAI_API_KEY")
        self.GROQ_API_KEY = self._get("GROQ_API_KEY")
        self.MISTRAL_API_KEY = self._get("MISTRAL_API_KEY")

        # ======================
        # MEMORY
        # ======================
        self.SUPABASE_URL = self._get("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = self._get("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = self._get("SUPABASE_SERVICE_ROLE_KEY")

        # ======================
        # TOOLS
        # ======================
        self.SERPAPI_KEY = self._get("SERPAPI_KEY")
        self.OPENWEATHER_API_KEY = self._get("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = self._get("MAPBOX_TOKEN")
        self.GOOGLE_MAPS_API_KEY = self._get("GOOGLE_MAPS_API_KEY")

        # ======================
        # SECURITY
        # ======================
        self.JWT_SECRET = self._get("JWT_SECRET")
        self.ENCRYPTION_KEY = self._get("ENCRYPTION_KEY")

        # ======================
        # PERFORMANCE
        # ======================
        self.REQUEST_TIMEOUT = int(self._get("REQUEST_TIMEOUT", 45))
        self.MAX_RETRIES = int(self._get("MAX_RETRIES", 2))

        self._validate()

    def _get(self, key: str, default: str = None):
        value = os.getenv(key, default)
        return str(value).strip() if value else default

    def _bool(self, key: str, default: bool = False):
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("1", "true", "yes", "on")

    def _validate(self):
        required = [
            "BOT_TOKEN",
            "SUPABASE_URL",
            "SUPABASE_SERVICE_ROLE_KEY",
            "JWT_SECRET",
            "ENCRYPTION_KEY",
        ]

        missing = [k for k in required if not getattr(self, k)]

        if missing:
            raise ValueError("Missing env vars: " + ", ".join(missing))

        if self.ENV == "production" and not self.WEBHOOK_URL:
            print("⚠️ WEBHOOK_URL missing → polling fallback will be used")