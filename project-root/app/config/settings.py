import os
import logging


class Settings:
    """
    Production-safe + cognition-aware configuration layer.
    Railway-safe version (no hard crash on missing env).
    """

    def __init__(self):

        # -------------------------
        # CORE KEYS
        # -------------------------
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        # -------------------------
        # SECURITY
        # -------------------------
        self.JWT_SECRET = os.getenv("JWT_SECRET")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

        # -------------------------
        # DATABASE
        # -------------------------
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # -------------------------
        # EXTERNAL APIs
        # -------------------------
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
        self.SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        self.BREVO_API_KEY = os.getenv("BREVO_API_KEY")

        # -------------------------
        # DEPLOYMENT
        # -------------------------
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL")

        # -------------------------
        # MODEL SYSTEM
        # -------------------------
        self.DEFAULT_MODEL_LAYERS = {
            "fast": ["groq/compound-mini"],
            "general": ["llama-3.3-70b-versatile"],
            "heavy": ["meta-llama/llama-4-scout-17b-16e-instruct"],
            "safety": ["openai/gpt-oss-safeguard-20b"],
        }

        self.MODEL_LAYERS = {
            "fast": [
                "groq/compound-mini",
                "llama-3.1-8b-instant",
            ],

            "general": [
                "llama-3.3-70b-versatile",
                "qwen/qwen3-32b",
                "openai/gpt-oss-20b",
            ],

            "heavy": [
                "openai/gpt-oss-120b",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ],

            "safety": [
                "openai/gpt-oss-safeguard-20b",
                "meta-llama/llama-prompt-guard-2-22m",
                "meta-llama/llama-prompt-guard-2-86m",
            ]
        }

        # -------------------------
        # INTENT MAPPING
        # -------------------------
        self.INTENT_TO_LAYER = {
            "fast": "fast",
            "reasoning": "heavy",
            "creative": "general",
            "general": "general",
            "safety": "safety"
        }

        self.DEFAULT_LAYER = "general"

        # -------------------------
        # BEHAVIOR MODES
        # -------------------------
        self.BEHAVIOR_MODES = {
            "FAST": "Be concise and direct.",
            "GENERAL": "Be balanced, clear and natural.",
            "HEAVY": "Use step-by-step deep reasoning.",
            "SAFETY": "Be neutral and factual."
        }

        # -------------------------
        # SYSTEM CAPABILITIES
        # -------------------------
        self.SYSTEM_CONFIG = {
            "multilingual": True,
            "olympiad_mode": True,
            "step_by_step_reasoning": True,
            "adaptive_routing": True,
            "cognition_loop": True
        }

        # -------------------------
        # RESPONSE TUNING
        # -------------------------
        self.RESPONSE_TUNING = {
            "max_retries_llm": 2,
            "max_retries_verifier": 2,
            "allow_long_reasoning": True,
            "prefer_structured_output": True,
            "avoid_fluff": True
        }

        # -------------------------
        # SAFE VALIDATION
        # -------------------------
        self._validate_soft()

    # -------------------------
    # SAFE VALIDATION
    # -------------------------
    def _validate_soft(self):
        missing = []

        required = [
            ("GROQ_API_KEY", self.GROQ_API_KEY),
            ("BOT_TOKEN", self.BOT_TOKEN)
        ]

        for name, value in required:
            if not value:
                missing.append(name)

        if missing:
            logging.warning(
                f"[CONFIG WARNING] Missing env vars: {', '.join(missing)}"
            )

    # -------------------------
    # HELPERS
    # -------------------------
    def get_models(self, layer: str):
        return self.MODEL_LAYERS.get(
            layer,
            self.DEFAULT_MODEL_LAYERS.get(layer, [])
        )

    def get_layer_by_intent(self, intent: str) -> str:
        return self.INTENT_TO_LAYER.get(intent, self.DEFAULT_LAYER)


# singleton
settings = Settings()