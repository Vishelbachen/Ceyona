from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    webhook_url: str = Field("", description="Public webhook URL")
    allowed_origins: str = Field("*", description="Comma-separated allowed origins")

    # ─── LLM PROVIDERS ──────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key")
    hf_token: str = Field(..., description="HuggingFace token")

    # ─── MEMORY / STORAGE ───────────────────────────────
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anon key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")
    redis_url: str = Field("redis://localhost:6379", description="Redis connection URL")

    # ─── EXTERNAL SERVICES ──────────────────────────────
    brevo_api_key: str = Field("", description="Brevo email API key")
    mapbox_token: str = Field("", description="Mapbox token")
    openweather_api_key: str = Field("", description="OpenWeather API key")
    serpapi_key: str = Field("", description="SerpAPI key")
    tavily_api_key: str = Field("", description="Tavily search API key")
    searxng_url: str = Field("", description="SearXNG instance URL")
    sentry_dsn: str = Field("", description="Sentry DSN")

    # ─── ECONOMY / TON ──────────────────────────────────
    ton_wallet: str = Field("", description="TON wallet address")

    # Platform margin applied at top-up time.
    # User receives (ton_amount × market_price × topup_rate) USD credits.
    # topup_rate = 1.0 / target_markup, e.g. 1.0/1.3 ≈ 0.769 for 30% gross margin.
    # Set to 1.0 to disable margin (testing / free period).
    # Change here only — no other billing code needs to be touched.
    topup_rate: float = Field(1.0, description="TON→USD conversion rate multiplier (< 1.0 activates platform margin)")

    # ─── CLOUDFLARE WORKER PROXY ────────────────────────
    # Set to your worker URL, e.g. https://ceyona-worker.your-subdomain.workers.dev
    # When set, all Telegram API calls (getFile, file downloads) go through
    # the worker's /tg/ proxy instead of api.telegram.org directly.
    telegram_proxy_url: str = Field("", description="Cloudflare Worker base URL for Telegram API proxy")
    webhook_secret: str = Field("", description="Secret token for Telegram webhook verification (set in HF and Cloudflare)")

    # ─── RUNTIME ────────────────────────────────────────
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field("production", description="Environment name")


# Singleton — import this everywhere
settings = Settings()