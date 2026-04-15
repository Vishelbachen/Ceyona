import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        # ======================
        # CORE BOT
        # ======================
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        # ======================
        # AI MODELS
        # ======================
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

        # ======================
        # MEMORY (SUPABASE)
        # ======================
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # ======================
        # APIS
        # ======================
        self.SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
        self.GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

        # ======================
        # PAYMENTS
        # ======================
        self.TON_WALLET = os.getenv("TON_WALLET")

        # ======================
        # SECURITY
        # ======================
        self.JWT_SECRET = os.getenv("JWT_SECRET")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

        # ======================
        # VALIDATION
        # ======================
        self._validate()

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
                f"Missing critical env vars: {', '.join(missing)}"
            )