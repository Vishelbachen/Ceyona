from app.engine.intent_classifier import classify_intent
from app.engine.model_policy import select_model_by_intent
from app.config.settings import settings
from app.engine.types import IntentResult

# 🔥 thresholds (tuned for stability)
LOW_CONFIDENCE = 0.55
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    🧠 SINGLE SOURCE OF TRUTH — MODEL DECISION ENGINE v3.2 (STABLE)

    PRINCIPLES:
    - deterministic fallback ALWAYS exists
    - reasoning priority > intent priority
    - intent is advisory, not authoritative
    """

    text = text or ""
    text_len = len(text)

    # 🧠 1. INTENT DETECTION (FUNCTIONAL VERSION)
    intent_result: IntentResult = classify_intent(text)
    intent = intent_result.intent

    # 🧠 2. REASONING OVERRIDE (CRITICAL FOR OLYMPIAD TASKS)
    if _is_reasoning_heavy(text):
        return settings.HEAVY_MODELS[0], intent_result

    # 🧠 3. LOW COMPLEXITY / LOW RELIABILITY PATH
    # (no trust in intent classifier)
    if _is_low_reliability(intent_result, text_len):
        return _size_based_model(text_len), intent_result

    # 🧠 4. POLICY LAYER (PRIMARY ROUTING SYSTEM)
    try:
        model = select_model_by_intent(intent_result)
        if model:
            return model, intent_result
    except Exception:
        # never crash decision engine
        pass

    # 🧠 5. FINAL SAFE FALLBACK
    return _size_based_model(text_len), intent_result


# -------------------------
# INTERNAL HELPERS
# -------------------------

def _size_based_model(text_len: int) -> str:
    """Pure deterministic fallback (NO ML DEPENDENCY)"""

    if text_len < SHORT_TEXT:
        return settings.FAST_MODELS[0]

    if text_len < MID_TEXT:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]


def _is_low_reliability(intent_result: IntentResult, text_len: int) -> bool:
    """
    When system should IGNORE intent entirely.

    This replaces confidence logic (removed in functional model).
    """

    # very short text = unstable classification
    if text_len < 20:
        return True

    # unknown / ambiguous intent
    if intent_result.intent not in {"fast", "chat", "reasoning", "creative", "safety"}:
        return True

    return False


def _is_reasoning_heavy(text: str) -> bool:
    """
    Detects olympiad / math / logic / proof tasks.
    Hard override for model stability.
    """

    text_lower = text.lower()

    triggers = [
        "докажи", "реши", "найди", "уравнение",
        "integral", "derive", "prove", "calculate",
        "матем", "логик", "алгеб", "геометр",
        "equation", "proof", "solve", "theorem"
    ]

    return any(t in text_lower for t in triggers)