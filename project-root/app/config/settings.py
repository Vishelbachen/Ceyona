import os


class Settings:
    """
    Production-safe configuration loader.
    Single source of truth for all environment variables.
    """

    def __init__(self):
        # 🔐 CORE
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")

        # 🔐 SECURITY
        self.JWT_SECRET = os.getenv("JWT_SECRET")
        self.ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

        # 🗄 DB (future)
        self.SUPABASE_URL = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # 🌐 EXTERNAL APIs
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
        self.MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
        self.SERPAPI_KEY = os.getenv("SERPAPI_KEY")
        self.BREVO_API_KEY = os.getenv("BREVO_API_KEY")

        # 🚀 DEPLOYMENT
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL")

        # 🧠 MODEL LAYERS (ROUTING SYSTEM)

        self.FAST_MODELS = [
            "groq/compound-mini",
            "llama-3.1-8b-instant",
        ]

        self.GENERAL_MODELS = [
            "llama-3.3-70b-versatile",
            "qwen/qwen3-32b",
            "openai/gpt-oss-20b",
        ]

        self.HEAVY_MODELS = [
            "openai/gpt-oss-120b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        ]

        self.SAFETY_MODELS = [
            "openai/gpt-oss-safeguard-20b",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
        ]

        # 🧠 INTENT SYSTEM

        self.DEFAULT_INTENT = "general"
        self.INTENT_CONFIDENCE_THRESHOLD = 0.6

        self.INTENT_MODEL_PRIORITY = {
            "fast": self.FAST_MODELS,
            "reasoning": self.HEAVY_MODELS,
            "creative": self.GENERAL_MODELS,
            "safety": self.SAFETY_MODELS,
            "general": self.GENERAL_MODELS,
        }

        # 🧠 BEHAVIOR MODES (NOW PURE PROMPT SIGNALS)

        self.BEHAVIOR_MODES = {
            "FAST": {
                "instruction": (
                    "Fast reasoning mode.\n"
                    "Be concise, direct, minimal wording.\n"
                    "Optimize for speed and clarity."
                )
            },

            "GENERAL": {
                "instruction": (
                    "Balanced assistant mode.\n"
                    "Respond clearly and naturally.\n"
                    "Adapt language to the user automatically.\n"
                )
            },

            "HEAVY": {
                "instruction": (
                    "Deep reasoning mode.\n"
                    "Solve problems step-by-step with full rigor.\n"
                    "Required for olympiad-level math, physics, CS, algorithms.\n"
                    "Prioritize correctness, structure, and completeness over speed."
                )
            },

            "SAFETY": {
                "instruction": (
                    "Safety reasoning mode.\n"
                    "Provide neutral, factual, non-harmful responses.\n"
                )
            }
        }

        # 🧠 GLOBAL SYSTEM CONFIG (NO MORE ANTI-IDENTITY RULES HERE)

        self.SYSTEM_CONFIG = {
            "multilingual": True,
            "olympiad_mode": True,
            "code_quality_priority": True,
            "step_by_step_reasoning": True,
        }

        # 🧠 RESPONSE BEHAVIOR TUNING (NEW IMPORTANT ADDITION)

        self.RESPONSE_TUNING = {
            "allow_long_reasoning": True,
            "prefer_structured_output_for_math": True,
            "prefer_clean_code": True,
            "avoid_fluff": True
        }

        # 🧯 VALIDATION

        self._validate()

    def _validate(self):
        missing = []

        if not self.BOT_TOKEN:
            missing.append("BOT_TOKEN")

        if not self.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")

        if not self.FAST_MODELS:
            missing.append("FAST_MODELS")

        if not self.GENERAL_MODELS:
            missing.append("GENERAL_MODELS")

        if not self.INTENT_MODEL_PRIORITY:
            missing.append("INTENT_MODEL_PRIORITY")

        if not self.BEHAVIOR_MODES:
            missing.append("BEHAVIOR_MODES")

        if missing:
            raise RuntimeError(
                f"[CONFIG ERROR] Missing env vars: {', '.join(missing)}"
            )


# singleton
settings = Settings()