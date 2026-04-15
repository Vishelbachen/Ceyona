import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):

        self.ENV = self._get("ENV", "production")

        # CORE
        self.BOT_TOKEN = self._get("BOT_TOKEN")
        self.WEBHOOK_URL = self._get("WEBHOOK_URL")

        # AI / MEMORY
        self.GEMINI_API_KEY = self._get("GEMINI_API_KEY")
        self.OPENAI_API_KEY = self._get("OPENAI_API_KEY")
        self.GROQ_API_KEY = self._get("GROQ_API_KEY")
        self.MISTRAL_API_KEY = self._get("MISTRAL_API_KEY")

        self.SUPABASE_URL = self._get("SUPABASE_URL")
        self.SUPABASE_SERVICE_ROLE_KEY = self._get("SUPABASE_SERVICE_ROLE_KEY")

        self.JWT_SECRET = self._get("JWT_SECRET")
        self.ENCRYPTION_KEY = self._get("ENCRYPTION_KEY")

        self.PORT = int(self._get("PORT", 8080))

        self._validate()

    def _get(self, key: str, default: str = None):
        v = os.getenv(key, default)
        return v.strip() if isinstance(v, str) else v

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
            raise ValueError(f"Missing env vars: {', '.join(missing)}")

        if self.ENV == "production" and not self.WEBHOOK_URL:
            print("⚠️ WEBHOOK_URL is empty (Railway production warning)")