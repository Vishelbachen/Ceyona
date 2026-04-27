from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


# =========================
# CORE SETTINGS
# =========================
@dataclass(frozen=True)
class Settings:
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
    BREVO_API_KEY: str
    MAPBOX_TOKEN: str
    OPENWEATHER_API_KEY: str
    SERPAPI_KEY: str
    SENTRY_DSN: str

    # =========================
    # ECONOMY / DEPLOYMENT
    # =========================
    TON_WALLET: str
    WEBHOOK_URL: str

    # =========================
    # POLICY / LIMITS (RUNTIME CONTROL)
    # =========================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    MAX_CONTEXT_TOKENS: int = 8000
    MAX_RESPONSE_TOKENS: int = 2000

    # =========================
    # MODEL DEFAULTS (v4.7 routing)
    # =========================
    FAST_MODEL: str = "llama-3.1-8b-instant"
    GENERAL_MODEL: str = "llama-3.3-70b-versatile"
    HEAVY_MODEL: str = "gpt-oss-120b"

    EMBEDDING_MODEL: str = "bge-large-en-v1.5"
    RERANKER_MODEL: str = "bge-reranker-large"

    # =========================
    # SECURITY POLICY
    # =========================
    ALLOWED_ORIGINS: List[str] = None

    # =========================
    # INIT SAFETY
    # =========================
    def __post_init__(self):
        object.__setattr__(
            self,
            "ALLOWED_ORIGINS",
            self.ALLOWED_ORIGINS or ["*"]
        )


# =========================
# ENV LOADER
# =========================
def get_settings() -> Settings:
    """
    SINGLE SOURCE OF TRUTH CONFIG LOADER
    """

    return Settings(
        # CORE
        BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
        JWT_SECRET=os.getenv("JWT_SECRET", ""),
        ENCRYPTION_KEY=os.getenv("ENCRYPTION_KEY", ""),

        # LLM
        GROQ_API_KEY=os.getenv("GROQ_API_KEY", ""),
        HF_TOKEN=os.getenv("HF_TOKEN", ""),

        # STORAGE
        SUPABASE_URL=os.getenv("SUPABASE_URL", ""),
        SUPABASE_ANON_KEY=os.getenv("SUPABASE_ANON_KEY", ""),
        SUPABASE_SERVICE_ROLE_KEY=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        REDIS_URL=os.getenv("REDIS_URL", ""),

        # EXTERNAL
        BREVO_API_KEY=os.getenv("BREVO_API_KEY", ""),
        MAPBOX_TOKEN=os.getenv("MAPBOX_TOKEN", ""),
        OPENWEATHER_API_KEY=os.getenv("OPENWEATHER_API_KEY", ""),
        SERPAPI_KEY=os.getenv("SERPAPI_KEY", ""),
        SENTRY_DSN=os.getenv("SENTRY_DSN", ""),

        # ECONOMY
        TON_WALLET=os.getenv("TON_WALLET", ""),
        WEBHOOK_URL=os.getenv("WEBHOOK_URL", ""),

        # LIMITS
        RATE_LIMIT_PER_MINUTE=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        RATE_LIMIT_WINDOW_SECONDS=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),

        MAX_CONTEXT_TOKENS=int(os.getenv("MAX_CONTEXT_TOKENS", "8000")),
        MAX_RESPONSE_TOKENS=int(os.getenv("MAX_RESPONSE_TOKENS", "2000")),

        # MODELS
        FAST_MODEL=os.getenv("FAST_MODEL", "llama-3.1-8b-instant"),
        GENERAL_MODEL=os.getenv("GENERAL_MODEL", "llama-3.3-70b-versatile"),
        HEAVY_MODEL=os.getenv("HEAVY_MODEL", "gpt-oss-120b"),

        EMBEDDING_MODEL=os.getenv("EMBEDDING_MODEL", "bge-large-en-v1.5"),
        RERANKER_MODEL=os.getenv("RERANKER_MODEL", "bge-reranker-large"),

        # SECURITY
        ALLOWED_ORIGINS=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    )