from functools import lru_cache
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """
    AI Platform v4.7 — SINGLE SOURCE OF TRUTH
    Runtime configuration layer (ENV registry only).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================
    # CORE APP
    # =========================
    APP_NAME: str = "AI Platform"
    APP_VERSION: str = "4.7"
    ENV: str = "production"
    DEBUG: bool = False

    # =========================
    # SECURITY / AUTH
    # =========================
    BOT_TOKEN: Optional[str] = None
    JWT_SECRET: Optional[str] = None
    ENCRYPTION_KEY: Optional[str] = None

    # FIX: list must be string in env, parsed safely
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if v is None or v == "":
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return ["*"]

    # =========================
    # LLM PROVIDERS
    # =========================
    GROQ_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None

    # =========================
    # MEMORY / STORAGE
    # =========================
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    REDIS_URL: Optional[str] = None

    # =========================
    # PAYMENT / ECONOMY (TON)
    # =========================
    TON_WALLET: Optional[str] = None

    # =========================
    # EXTERNAL SERVICES
    # =========================
    BREVO_API_KEY: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

    # =========================
    # OBSERVABILITY
    # =========================
    SENTRY_DSN: Optional[str] = None

    # =========================
    # INFRASTRUCTURE
    # =========================
    WEBHOOK_URL: Optional[str] = None

    # =========================
    # FEATURE FLAGS
    # =========================
    FEATURE_RETRIEVAL: bool = True
    FEATURE_RERANKING: bool = True
    FEATURE_MEMORY: bool = True
    FEATURE_AGENTS: bool = True

    # =========================
    # PERFORMANCE / LIMITS
    # =========================
    ENABLE_CACHE: bool = True
    ENABLE_METRICS: bool = True
    ENABLE_TRACING: bool = True

    MAX_TOKENS_FAST: int = 300
    MAX_TOKENS_GENERAL: int = 1200
    MAX_TOKENS_HEAVY: int = 3000


# =========================
# SINGLETON ACCESS
# =========================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached global settings instance.
    """
    return Settings()