from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── CORE ───────────────────────────────────────────
    bot_token: str = Field(..., description="Telegram bot token")
    jwt_secret: str = Field(..., description="JWT signing secret")
    encryption_key: str = Field(..., description="Fernet encryption key")
    webhook_url: str = Field(..., description="Public webhook URL")
    allowed_origins: str = Field("*", description="Comma-separated allowed origins")

    # ─── LLM PROVIDERS ──────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key")
    hf_token: str = Field(..., description="HuggingFace token")

    # ─── MEMORY / STORAGE ───────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")

    EXTERNAL SERVICES ──────────────────────────────
    brevo_api_key: str = Field("", description="Brevo email API key")
    mapbox_token: str = Field("", description="Mapbox token")
    openweather_api_key: str = Field("", description="OpenWeather API key")
    serpapi_key: str = Field("", description="SerpAPI key")
    tavily_api_key: str = Field("", description="Tavily search API key")
    tavily_api_key: str = Field("", description="Tavily API key")
    sentry_dsn: str = Field("", description="Sentry DSN")

    # ─── ECONOMY / TON ──────────────────────────────────
    ton_wallet: str = Field("", description="TON wallet address")

    # ─── RUNTIME ────────────────────────────────────────
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field("production", description="Environment name")


# Singleton — import this everywhere
settings = Settings()