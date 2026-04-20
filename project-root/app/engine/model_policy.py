from app.config.settings import settings
from app.engine.intent_classifier import IntentResult


def select_model_by_intent(intent: IntentResult) -> str:

    if intent.intent == "safety":
        return settings.SAFETY_MODELS[0]

    if intent.intent == "reasoning":
        return settings.HEAVY_MODELS[0]

    if intent.intent == "creative":
        return settings.GENERAL_MODELS[0]

    if intent.intent == "fast":
        return settings.FAST_MODELS[0]

    return settings.GENERAL_MODELS[0]