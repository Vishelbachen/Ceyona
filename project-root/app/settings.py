from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================
# SETTINGS CORE
# =========================
class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================
    # CORE SECURITY
    # =========================
    BOT_TOKEN: str
    JWT_SECRET: str
    ENCRYPTION_KEY: str

    # =========================
    # LLM PROVIDERS
    # =========================
    GROQ_API_KEY: str
    HF_TOKEN: str

    # =========================
    # MEMORY / STORAGE
    # =========================
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    REDIS_URL: str

    # =========================
    # EXTERNAL SERVICES
    # =========================
    BREVO_API_KEY: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    # =========================
    # ECONOMY / DEPLOYMENT
    # =========================
    TON_WALLET: str
    WEBHOOK_URL: Optional[str] = None


# =========================
# SINGLETON ACCESS (DI SAFE)
# =========================
@lru_cache
def get_settings() -> Settings:
    return Settings()