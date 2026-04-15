class Constants:
    """
    Central system constants for AI orchestration engine
    """

    # AI behavior
    MAX_MEMORY_MESSAGES = 50
    MAX_REASONING_STEPS = 5

    # scoring thresholds
    MIN_SCORE_ACCEPT = 2
    HIGH_SCORE_BONUS = 4

    # routing keys
    ROUTES = {
        "CODING": "coding",
        "KNOWLEDGE": "knowledge",
        "GENERAL": "general",
        "WEATHER": "weather",
        "MAPS": "maps"
    }

    # tool names
    TOOLS = {
        "SEARCH": "search",
        "WEATHER": "weather",
        "MAPS": "maps",
        "ANALYTICS": "analytics"
    }

    # system limits
    STREAM_CHUNK_SIZE = 4
    THREAD_HISTORY_LIMIT = 100