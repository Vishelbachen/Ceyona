FAST_MODELS = [
    "groq/compound-mini",
    "llama-3.1-8b-instant"
]

GENERAL_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "openai/gpt-oss-20b"
]

HEAVY_MODELS = [
    "openai/gpt-oss-120b",
    "meta-llama/llama-4-scout-17b-16e-instruct"
]


def select_model(text: str) -> str:
    """
    MVP router (deterministic, stable)
    """

    text_len = len(text)

    # очень короткие запросы → fast
    if text_len < 50:
        return FAST_MODELS[0]

    # средние → general
    if text_len < 300:
        return GENERAL_MODELS[0]

    # длинные / сложные → heavy
    return HEAVY_MODELS[0]