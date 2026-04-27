from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List, Optional


# =========================
# SETTINGS MODEL
# =========================
@dataclass
class Settings:
    """
    SINGLE SOURCE OF TRUTH (v4.7)

    Contains:
    - secrets
    - limits
    - model config
    - pricing config
    - system toggles
    """

    # =========================
    # CORE SECURITY
    # =========================
    BOT_TOKEN: str
    JWT_SECRET: str
    ENCRYPTION_KEY: str

    ALLOWED_ORIGINS: List[str]

    # =========================
    # RATE LIMITING
    # =========================
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW: int = 60

    # =========================
    # LLM PROVIDERS
    # =========================
    GROQ_API_KEY: str
    HF_TOKEN: str

    # =========================
    # MODEL DEFAULTS
    # =========================
    FAST_MODEL: str = "llama-3.1-8b-instant"
    GENERAL_MODEL: str = "llama-3.3-70b-versatile"
    HEAVY_MODEL: str = "gpt-oss-120b"
    SAFETY_MODEL: str = "gpt-oss-safeguard-20b"

    # =========================
    # PRICING (INTERNAL CREDITS)
    # =========================
    BASE_COST: float = 0.001

    COST_FAST: float = 0.002
    COST_GENERAL: float = 0.01
    COST_HEAVY: float = 0.05

    # =========================
    # TON ECONOMY LAYER
    # =========================
    TON_WALLET: str
    TON_TO_CREDITS_RATE: int = 5000

    # =========================
    # MEMORY / STORAGE
    # =========================
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # =========================
    # EXTERNAL SERVICES
    # =========================
    OPENWEATHER_API_KEY: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    # =========================
    # SYSTEM
    # =========================
    WEBHOOK_URL: Optional[str] = None

    # =========================
    # LOAD FROM ENV
    # =========================
    @staticmethod
    def load() -> "Settings":
        return Settings(
            BOT_TOKEN=os.getenv("BOT_TOKEN"),
            JWT_SECRET=os.getenv("JWT_SECRET"),
            ENCRYPTION_KEY=os.getenv("ENCRYPTION_KEY"),

            
            GROQ_API_KEY=os.getenv("GROQ_API_KEY"),
            HF_TOKEN=os.getenv("HF_TOKEN"),

            TON_WALLET=os.getenv("TON_WALLET"),

            SUPABASE_URL=os.getenv("SUPABASE_URL"),
            SUPABASE_ANON_KEY=os.getenv("SUPABASE_ANON_KEY"),
            SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            REDIS_URL=os.getenv("REDIS_URL"),

            OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY"),
            MAPBOX_TOKEN=os.getenv("MAPBOX_TOKEN"),
            SERPAPI_KEY=os.getenv("SERPAPI_KEY"),
            SENTRY_DSN=os.getenv("SENTRY_DSN"),

            WEBHOOK_URL=os.getenv("WEBHOOK_URL"),
        )


# =========================
# SINGLETON ACCESSOR
# =========================
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings

    if _settings is None:
        _settings = Settings.load()

    return _settings