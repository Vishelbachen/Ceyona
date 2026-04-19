from app.engine.intent_classifier import IntentClassifier
from app.engine.model_policy import select_model_by_intent
from app.config.settings import settings
from app.engine.types import IntentResult

# 🔥 thresholds (tuned for stability)
LOW_CONFIDENCE = 0.55
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    🧠 SINGLE SOURCE OF TRUTH — MODEL DECISION ENGINE v3.1

    CORE IDEA:
    - intent is helpful, but NEVER dominant over reasoning stability
    - deterministic fallback always preserved
    - reasoning-heavy queries get priority stability
    """

    text = text or ""
    text_len = len(text)

    # 🧠 1. INTENT DETECTION
    intent_result = IntentClassifier.classify(text)
    intent = intent_result.intent
    confidence = intent_result.confidence

    # 🧠 2. PRE-CHECK: REASONING OVERRIDE (IMPORTANT FIX FOR OLYMPIADS)
    # если текст похож на задачу → всегда усиливаем модель
    if _is_reasoning_heavy(text):
        return settings.HEAVY_MODELS[0], intent_result

    # 🧠 3. LOW CONFIDENCE → PURE SIZE LOGIC (NO INTENT RELIANCE)
    if confidence < LOW_CONFIDENCE:
        return _size_based_model(text_len), intent_result

    # 🧠 4. POLICY ROUTING (PRIMARY SYSTEM)
    try:
        model = select_model_by_intent(intent_result)
        if model:
            return model, intent_result
    except Exception:
        pass

    # 🧠 5. FALLBACK (SAFE DETERMINISTIC PATH)
    return _size_based_model(text_len), intent_result


# -------------------------
# INTERNAL HELPERS
# -------------------------

def _size_based_model(text_len: int) -> str:
    """Pure deterministic fallback (NO INTENT DEPENDENCY)"""

    if text_len < SHORT_TEXT:
        return settings.FAST_MODELS[0]

    if text_len < MID_TEXT:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]


def _is_reasoning_heavy(text: str) -> bool:
    """
    Detects olympiad / math / logic / reasoning tasks.

    WHY:
    prevents weak model selection even when intent classifier fails
    """

    text_lower = text.lower()

    triggers = [
        "докажи", "реши", "найди", "уравнение",
        "integral", "derive", "prove", "calculate",
        "матем", "логик", "алгеб", "геометр",
        "equation", "proof", "solve", "theorem"
    ]

    return any(t in text_lower for t in triggers)