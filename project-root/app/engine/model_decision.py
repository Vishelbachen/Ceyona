from app.engine.intent_classifier import IntentClassifier
from app.engine.model_policy import select_model_by_intent
from app.engine.model_router import select_model as legacy_fallback
from app.config.settings import settings
from app.engine.types import IntentResult

# 🔥 thresholds (в будущем можно перенести в settings)
LOW_CONFIDENCE = 0.55
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    🧠 SINGLE SOURCE OF TRUTH — MODEL DECISION ENGINE v2

    Pipeline:
    1. Intent classification
    2. Confidence gate
    3. Policy routing (primary)
    4. Legacy fallback (safety net)
    5. Deterministic size-based fallback
    """

    text = text or ""
    text_len = len(text)

    # 🧠 1. INTENT DETECTION
    intent_result = IntentClassifier.classify(text)

    intent = intent_result.intent
    confidence = intent_result.confidence

    # 🧠 2. LOW CONFIDENCE → BYPASS INTENT SYSTEM
    if confidence < LOW_CONFIDENCE:
        try:
            return legacy_fallback(text), intent_result
        except Exception:
            return settings.GENERAL_MODELS[0], intent_result

    # 🧠 3. PRIMARY POLICY ROUTING
    try:
        model = select_model_by_intent(intent_result)
        if model:
            return model, intent_result
    except Exception:
        pass

    # 🧠 4. STRUCTURED FALLBACK (SIZE-AWARE)
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