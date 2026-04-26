from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =========================
# 🧱 BASE CONFIG
# =========================
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =========================
    # 📡 APP CORE
    # =========================
    BOT_TOKEN: str
    WEBHOOK_URL: str

    # =========================
    # 🔐 SECURITY
    # =========================
    JWT_SECRET: str = Field(min_length=16)
    ENCRYPTION_KEY: str = Field(min_length=16)
    ALLOWED_ORIGINS: List[str] = Field(default_factory=list)

    # =========================
    # 🤖 LLM PROVIDERS
    # =========================
    GROQ_API_KEY: str
    HF_TOKEN: Optional[str] = None

    # =========================
    # 🧠 MEMORY / STORAGE
    # =========================
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    REDIS_URL: str

    # =========================
    # 🌍 EXTERNAL SERVICES
    # =========================
    BREVO_API_KEY: Optional[str] = None
    MAPBOX_TOKEN: Optional[str] = None
    OPENWEATHER_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

    # =========================
    # 💳 ECONOMY / BLOCKCHAIN
    # =========================
    TON_WALLET: Optional[str] = None

    # =========================
    # 📊 OBSERVABILITY
    # =========================
    SENTRY_DSN: Optional[str] = None

    # =========================
    # ⚙️ INTERNAL FLAGS (future-proof)
    # =========================
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # =========================
    # 🧠 VALIDATION LAYER
    # =========================
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """
        Supports:
        - "a,b,c"
        - ["a", "b"]
        - "a"
        """
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("JWT_SECRET", "ENCRYPTION_KEY")
    @classmethod
    def validate_secrets(cls, v: str):
        if len(v) < 16:
            raise ValueError("Secret must be at least 16 characters")
        return v


# =========================
# ⚡ SINGLETON ACCESSOR
# =========================
@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton settings instance.
    Used by bootstrap + DI container.
    """
    return Settings()


# =========================
# 🧩 GLOBAL ACCESS (SAFE)
# =========================
settings = get_settings()