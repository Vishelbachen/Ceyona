from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================
# SETTINGS CORE
# =========================
class Settings(BaseSettings):
    """
    Single source of truth for environment configuration.

    ROLE:
    - load environment variables
    - normalize configuration
    - provide DI-safe settings object

    DOES NOT:
    - contain business logic
    - interact with runtime systems
    - perform I/O operations beyond env loading
    """

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
    # SECURITY POLICY
    # =========================
    ALLOWED_ORIGINS: List[str] = Field(default_factory=list)

    # =========================
    # VALIDATION / NORMALIZATION
    # =========================
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """
        Supports:
        - "a.com,b.com"
        - ["a.com", "b.com"]
        - None
        """

        if v is None:
            return []

        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]

        if isinstance(v, list):
            return v

        return []


# =========================
# SINGLETON ACCESS (DI SAFE)
# =========================
@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance for dependency injection.

    IMPORTANT:
    - never reloaded at runtime
    - ensures deterministic configuration across system
    """
    return Settings()