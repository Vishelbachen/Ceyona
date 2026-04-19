from app.engine.intent_classifier import IntentClassifier
from app.engine.model_policy import select_model_by_intent
from app.engine.model_router import select_model as legacy_fallback
from app.config.settings import settings
from app.engine.types import IntentResult


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    Unified model decision layer (SOURCE OF TRUTH).

    Pipeline:
    1. Intent classification
    2. Policy-based routing
    3. Legacy fallback (safety net)
    """

    # 🧠 1. INTENT DETECTION
    intent_result = IntentClassifier.classify(text)

    try:
        # 🧠 2. POLICY ROUTING (PRIMARY SYSTEM)
        model = select_model_by_intent(intent_result)

        if model:
            return model, intent_result

    except Exception:
        # policy failure must not break system
        pass

    try:
        # 🧠 3. LEGACY ROUTER (SAFE FALLBACK)
        model = legacy_fallback(text)

        if model:
            return model, intent_result

    except Exception:
        # absolute fallback
        pass

    # 🧯 4. FINAL SAFETY NET
    return settings.GENERAL_MODELS[0], intent_result