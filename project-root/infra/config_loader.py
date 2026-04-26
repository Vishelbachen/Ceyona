from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Union


# =========================
# SETTINGS MODEL
# =========================
@dataclass(frozen=True)
class Settings:
    """
    Central configuration object.

    ROLE:
    - provide typed access to environment variables
    - ensure single source of truth for system config

    STRICT RULES:
    - no runtime logic
    - no network calls
    - no mutation after initialization
    """

    # CORE SECRETS
    BOT_TOKEN: str
    JWT_SECRET: str
    ENCRYPTION_KEY: str

    # LLM PROVIDERS
    GROQ_API_KEY: str
    HF_TOKEN: Optional[str] = None

    # MEMORY / STORAGE
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # EXTERNAL SERVICES
    BREVO_API_KEY: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    # ECONOMY / DEPLOYMENT
    TON_WALLET: Optional[str] = None
    WEBHOOK_URL: Optional[str] = None
    ALLOWED_ORIGINS: List[str] = None


# =========================
# LOADER
# =========================
def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


# =========================
# SINGLETON CACHE
# =========================
_settings_instance: Optional[Settings] = None


# =========================
# PUBLIC ACCESSOR
# =========================
def get_settings() -> Settings:
    """
    Lazy-loaded singleton settings object.
    """

    global _settings_instance

    if _settings_instance is not None:
        return _settings_instance

    _settings_instance = Settings(
        # CORE
        BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
        JWT_SECRET=os.getenv("JWT_SECRET", ""),
        ENCRYPTION_KEY=os.getenv("ENCRYPTION_KEY", ""),

        # LLM
        GROQ_API_KEY=os.getenv("GROQ_API_KEY", ""),
        HF_TOKEN=os.getenv("HF_TOKEN"),

        # STORAGE
        SUPABASE_URL=os.getenv("SUPABASE_URL"),
        SUPABASE_ANON_KEY=os.getenv("SUPABASE_ANON_KEY"),
        SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        REDIS_URL=os.getenv("REDIS_URL"),

        # EXTERNAL
        BREVO_API_KEY=os.getenv("BREVO_API_KEY"),
        MAPBOX_TOKEN=os.getenv("MAPBOX_TOKEN"),
        OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY"),
        SERPAPI_KEY=os.getenv("SERPAPI_KEY"),
        SENTRY_DSN=os.getenv("SENTRY_DSN"),

        # ECONOMY / DEPLOYMENT
        TON_WALLET=os.getenv("TON_WALLET"),
        WEBHOOK_URL=os.getenv("WEBHOOK_URL"),
        ALLOWED_ORIGINS=_parse_list(os.getenv("ALLOWED_ORIGINS")),
    )

    return _settings_instance