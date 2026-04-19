"""
Legacy fallback router.
# DO NOT IMPORT OUTSIDE model_decision.py
# EMERGENCY FALLBACK ONLY

⚠️ DO NOT USE as primary routing logic.
Primary system:
IntentClassifier → ModelPolicy → Settings
"""

from app.config.settings import settings


def select_model(text: str, intent_fallback: str | None = None) -> str:
    """
    Fallback model selector (ONLY for safety / emergency cases).

    Priority:
    1. intent fallback (if provided)
    2. heuristic fallback
    3. safe default
    """

    text_len = len(text)

    # 🧠 if intent already known → respect new system
    if intent_fallback:
        if intent_fallback == "safety":
            return settings.SAFETY_MODELS[0]

        if intent_fallback == "reasoning":
            return settings.HEAVY_MODELS[0]

        if intent_fallback == "creative":
            return settings.GENERAL_MODELS[0]

        if intent_fallback == "fast":
            return settings.FAST_MODELS[0]

        return settings.GENERAL_MODELS[0]

    # ⚠️ LEGACY MODE (only if no intent system used)
    if text_len < 50:
        return settings.FAST_MODELS[0]

    if text_len < 300:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]