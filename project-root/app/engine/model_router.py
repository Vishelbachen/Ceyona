"""
Legacy fallback router.
DO NOT USE AS PRIMARY LOGIC.

Used only when ModelDecision fails.
"""

from app.config.settings import settings


def select_model(text: str, intent_fallback: str | None = None) -> str:
    text_len = len(text)

    # 🧠 intent-based routing
    if intent_fallback:
        match intent_fallback:
            case "safety":
                return settings.SAFETY_MODELS[0]
            case "reasoning":
                return settings.HEAVY_MODELS[0]
            case "creative":
                return settings.GENERAL_MODELS[0]
            case "fast":
                return settings.FAST_MODELS[0]
            case _:
                return settings.GENERAL_MODELS[0]

    # ⚡ fallback heuristics
    if text_len < 50:
        return settings.FAST_MODELS[0]

    if text_len < 300:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]