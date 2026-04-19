from app.engine.intent_classifier import IntentClassifier
from app.engine.model_policy import select_model_by_intent
from app.engine.model_router import select_model as legacy_fallback
from app.config.settings import settings
from app.engine.types import IntentResult


# 🔥 thresholds (можно позже вынести в settings)
LOW_CONFIDENCE = 0.55
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    HYBRID MODEL DECISION LAYER v2

    Enhancements:
    - intent confidence aware routing
    - hybrid length + intent logic
    - safer fallback prioritization
    """

    text = text or ""
    text_len = len(text)

    # 🧠 1. INTENT DETECTION
    intent_result = IntentClassifier.classify(text)

    intent = intent_result.intent
    confidence = intent_result.confidence

    # 🧠 2. LOW CONFIDENCE → SKIP INTENT POLICY
    if confidence < LOW_CONFIDENCE:
        try:
            model = legacy_fallback(text)
            return model, intent_result
        except Exception:
            return settings.GENERAL_MODELS[0], intent_result

    # 🧠 3. STRONG INTENT → POLICY ROUTING
    try:
        model = select_model_by_intent(intent_result)

        if model:
            return model, intent_result
    except Exception:
        pass

    # 🧠 4. HYBRID SIZE-AWARE FALLBACK (IMPROVED LEGACY)
    try:
        if text_len < SHORT_TEXT:
            return settings.FAST_MODELS[0], intent_result

        if text_len < MID_TEXT:
            return settings.GENERAL_MODELS[0], intent_result

        return settings.HEAVY_MODELS[0], intent_result

    except Exception:
        pass

    # 🧯 5. ABSOLUTE SAFETY NET
    return settings.GENERAL_MODELS[0], intent_result