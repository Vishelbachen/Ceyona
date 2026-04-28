from functools import lru_cache
from typing import Optional, Any
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

    # FIX: raw string first (avoid Pydantic JSON crash)
    ALLOWED_ORIGINS: Any = Field(default="*")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any):
        return _safe_json_list(v, ["*"])

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
# SAFE JSON PARSER (v4.7 FIXED)
# =========================

def _safe_json(value: Any, default: Any):
    if value is None or value == "":
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _safe_json_list(value: Any, default: list):
    parsed = _safe_json(value, default)

    if isinstance(parsed, list):
        return parsed

    return default


# =========================
# SINGLETON ACCESS
# =========================

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()