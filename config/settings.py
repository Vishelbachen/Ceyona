import os
from dotenv import load_dotenv


class Settings:
    def __init__(self):
        load_dotenv()

        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        self.SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
        self.GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

        self.TON_WALLET = os.getenv("TON_WALLET")

        self._validate()

    def _validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")