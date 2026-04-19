from app.engine.intent_classifier import IntentClassifier
from app.engine.model_policy import select_model_by_intent
from app.config.settings import settings
from app.engine.types import IntentResult

# 🔥 thresholds
LOW_CONFIDENCE = 0.55
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    🧠 SINGLE SOURCE OF TRUTH — MODEL DECISION ENGINE v3 (CLEAN)

    Pipeline:
    1. Intent classification
    2. Confidence gate
    3. Policy routing
    4. Deterministic fallback (NO LEGACY ROUTER)
    """

    text = text or ""
    text_len = len(text)

    # 🧠 1. INTENT DETECTION
    intent_result = IntentClassifier.classify(text)
    intent = intent_result.intent
    confidence = intent_result.confidence

    # 🧠 2. LOW CONFIDENCE → SKIP INTENT LOGIC (BUT NOT LEGACY ROUTER)
    if confidence < LOW_CONFIDENCE:
        if text_len < SHORT_TEXT:
            return settings.FAST_MODELS[0], intent_result

        if text_len < MID_TEXT:
            return settings.GENERAL_MODELS[0], intent_result

        return settings.HEAVY_MODELS[0], intent_result

    # 🧠 3. POLICY ROUTING (PRIMARY SYSTEM)
    try:
        model = select_model_by_intent(intent_result)
        return model, intent_result
    except Exception:
        pass

    # 🧠 4. SIZE-BASED FALLBACK (SAFE DETERMINISTIC LOGIC)
    if text_len < SHORT_TEXT:
        return settings.FAST_MODELS[0], intent_result

    if text_len < MID_TEXT:
        return settings.GENERAL_MODELS[0], intent_result

    return settings.HEAVY_MODELS[0], intent_result