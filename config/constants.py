class Constants:

    # =========================
    # SYSTEM LIMITS (CORE SAFETY)
    # =========================
    MAX_MEMORY_ITEMS = 50
    MAX_RESPONSE_TOKENS = 2000
    MAX_USER_INPUT_LENGTH = 8000

    # =========================
    # TIMEOUTS (STABILITY LAYER)
    # =========================
    REQUEST_TIMEOUT_SECONDS = 45
    AI_RETRY_ATTEMPTS = 2

    # =========================
    # MEMORY CONFIG
    # =========================
    MEMORY_EMBEDDING_MODEL = "text-embedding-3-small"
    MEMORY_TOP_K = 5
    MEMORY_ENABLE_CACHE = True

    # =========================
    # AI ROUTING (SMART FALLBACK SYSTEM)
    # =========================
    DEFAULT_MODEL = "gemini"
    FALLBACK_MODEL = "groq"

    ENABLE_MULTI_MODEL_ROUTING = True
    ENABLE_AUTO_FALLBACK = True

    # =========================
    # MODEL PRIORITY ORDER
    # =========================
    MODEL_PRIORITY = [
        "gemini",
        "openai",
        "groq",
        "mistral"
    ]

    # =========================
    # PAYMENT SYSTEM
    # =========================
    DEFAULT_PLAN = "free"
    PREMIUM_PLAN = "pro"

    FREE_REQUEST_LIMIT = 30
    PRO_REQUEST_LIMIT = 500

    # =========================
    # SECURITY
    # =========================
    TOKEN_EXPIRE_MINUTES = 60
    MAX_LOGIN_ATTEMPTS = 5

    # =========================
    # ENGINE BEHAVIOR FLAGS
    # =========================
    ENABLE_BRAIN_LAYER = True
    ENABLE_REASONING_LAYER = True
    ENABLE_SELF_CORRECTION = True
    ENABLE_SELF_IMPROVE = True

    # =========================
    # LOGGING
    # =========================
    LOG_LEVEL = "INFO"
    ENABLE_DEBUG_TRACE = False