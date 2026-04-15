class Constants:

    # ======================
    # SYSTEM LIMITS
    # ======================
    MAX_MEMORY_ITEMS = 50
    MAX_RESPONSE_TOKENS = 2000

    # ======================
    # MEMORY CONFIG
    # ======================
    MEMORY_EMBEDDING_MODEL = "text-embedding-3-small"

    # ======================
    # AI DEFAULT ROUTING
    # ======================
    DEFAULT_MODEL = "gemini"
    FALLBACK_MODEL = "groq"

    # ======================
    # PAYMENT SYSTEM
    # ======================
    DEFAULT_PLAN = "free"
    PREMIUM_PLAN = "pro"

    # ======================
    # SECURITY
    # ======================
    TOKEN_EXPIRE_MINUTES = 60