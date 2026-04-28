from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    # ===== CORE AUTH =====
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    # ===== LLM PROVIDERS =====
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # ===== DATABASE (SUPABASE) =====
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # ===== INFRA =====
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # ===== EXTERNAL TOOLS =====
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    MAPBOX_TOKEN: str = os.getenv("MAPBOX_TOKEN", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")

    # ===== PAYMENTS (TON) =====
    TON_WALLET: str = os.getenv("TON_WALLET", "")

    # ===== EMAIL / NOTIFS =====
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")

    # ===== DEPLOY =====
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

    # ===== FLAGS =====
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"