# settings.py
# v4.7 Runtime Configuration Layer (minimal bootstrap)

import os


class Settings:
    """
    Central configuration registry.
    No external dependencies. Pure env-based config.
    """

    # =========================
    # LLM API KEYS
    # =========================
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    HF_TOKEN = os.getenv("HF_TOKEN", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # =========================
    # STORAGE / MEMORY
    # =========================
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    REDIS_URL = os.getenv("REDIS_URL", "")

    # =========================
    # OBSERVABILITY
    # =========================
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")

    # =========================
    # ECONOMY / BILLING
    # =========================
    TON_WALLET = os.getenv("TON_WALLET", "")
    BILLING_ENABLED = os.getenv("BILLING_ENABLED", "false").lower() == "true"

    # =========================
    # MODEL ROUTING IDS
    # =========================
    MODELS = {
        "FAST": "llama-3.1-8b-instant",
        "GENERAL": "llama-3.3-70b",
        "HEAVY": "gpt-oss-120b",
        "FALLBACK": "hf-internal-mock"
    }

    # =========================
    # COST MODEL (v4.7)
    # =========================
    MODEL_RATES = {
        "FAST": {"in": 0.25, "out": 0.9},
        "GENERAL": {"in": 2.5, "out": 10},
        "HEAVY": {"in": 8, "out": 30},
    }

    # =========================
    # EP KERNEL LIMITS
    # =========================
    MAX_COST_THRESHOLD = float(os.getenv("MAX_COST_THRESHOLD", "0.3"))

    @classmethod
    def validate(cls):
        """
        Lightweight sanity check (non-blocking).
        """
        return True