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

    # ─── ATTACHMENT LAYER (infra/attachment.py) ─────────
    # Storage bucket used by Worker for all Telegram attachments (voice/photo/document/…).
    # This is a bucket-housekeeping setting only — NOT a per-model size limit.
    # Per-model limits (Whisper 25MB, Vision 4MB base64 / 20MB URL, etc.) live inside
    # the respective handler (speech_to_text.py, vision_handler.py), not here.
    attachment_bucket: str = Field("telegram-attachments", description="Supabase Storage bucket for Telegram attachments")

    # Default TTL for signed URLs handed to external providers (Groq, etc.).
    # Short-lived on purpose — these files may contain private user content.
    attachment_signed_url_ttl_seconds: int = Field(300, description="Signed URL expiry for attachment access by external APIs")

    # Per-provider capability flags — whether the provider's API is confirmed to
    # accept a fetch-by-URL parameter for this attachment kind. Each flag gates
    # the URL-first path in its handler; when False, the handler uses attachment.bytes()
    # instead. Flip to True only after an empirical confirmation call against the
    # real API (see comments at each handler call site) — do not flip on documentation
    # alone, since privately-signed URLs may behave differently than public ones.
    #
    # STATUS (2026-07): all three flags below are now empirically CONFIRMED (see
    # architecture_reality.md tests 1-3). They're kept as flags rather than
    # inlined as constants for one to two more releases, as a rollback switch
    # in case something about the confirmed behavior turns out to be
    # environment-specific (e.g. this Groq account/tier only) rather than
    # general. TODO: if no regression surfaces by ~2026-09, remove these three
    # flags entirely and hardcode the confirmed behavior in each handler —
    # a flag that can only ever be set to its default is just a note pretending
    # to be a setting.
    groq_whisper_accepts_signed_url: bool = Field(
        True, description="Groq Whisper audio.transcriptions accepts url= for a Supabase signed URL — CONFIRMED empirically 2026-07 (test 3), once sent as a pure files= multipart request with no data= (see speech_to_text.py transcribe())"
    )
    groq_vision_accepts_signed_url: bool = Field(
        True, description="Groq vision chat completions accepts image_url pointing to a Supabase signed URL — CONFIRMED empirically 2026-07 (test 2), reproduced on a second run"
    )
    groq_whisper_accepts_ogg_opus: bool = Field(
        True, description="Groq Whisper accepts OGG/Opus directly without local WAV conversion — CONFIRMED empirically 2026-07 (test 1) against a real Telegram voice message (.oga renamed to .ogg, same bytes, no re-encoding); previously only confirmed via Groq docs at the format level, codec-level behavior was unverified until this test"
    )

    # ─── RUNTIME ────────────────────────────────────────
    debug: bool = Field(False, description="Debug mode")
    environment: str = Field("production", description="Environment name")


# Singleton — import this everywhere
settings = Settings()