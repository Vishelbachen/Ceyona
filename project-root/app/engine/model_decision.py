from app.engine.intent_classifier import classify_intent
from app.engine.model_policy import select_model_by_intent
from app.config.settings import settings
from app.engine.types import IntentResult

# Stability thresholds (routing heuristics)
SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    """
    SINGLE SOURCE OF TRUTH - MODEL DECISION ENGINE v3.3

    Design principles:
    - deterministic fallback always guaranteed
    - reasoning priority overrides intent system
    - intent is advisory signal only
    """

    text = text or ""
    text_len = len(text)

    # 1. Intent detection
    intent_result: IntentResult = classify_intent(text)

    # 2. Hard reasoning override (high stability priority)
    if _is_reasoning_heavy(text):
        return settings.HEAVY_MODELS[0], intent_result

    # 3. Reliability filter (ignore weak signals)
    if _is_low_reliability(intent_result, text_len):
        return _size_based_model(text_len), intent_result

    # 4. Policy routing (primary system)
    try:
        model = select_model_by_intent(intent_result)
        if model:
            return model, intent_result
    except Exception:
        # fail-safe: never break pipeline
        pass

    # 5. deterministic fallback
    return _size_based_model(text_len), intent_result


# -------------------------
# INTERNAL ROUTING HELPERS
# -------------------------

def _size_based_model(text_len: int) -> str:
    """
    Deterministic fallback without ML dependency
    """

    if text_len < SHORT_TEXT:
        return settings.FAST_MODELS[0]

    if text_len < MID_TEXT:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]


def _is_low_reliability(intent_result: IntentResult, text_len: int) -> bool:
    """
    Filters unstable or ambiguous intent predictions
    """

    if text_len < 20:
        return True

    valid_intents = {"fast", "reasoning", "creative", "safety", "general"}

    if intent_result.intent not in valid_intents:
        return True

    return False


def _is_reasoning_heavy(text: str) -> bool:
    """
    Detects high-complexity reasoning tasks:
    math, physics, logic, proofs, algorithms
    """

    t = text.lower()

    triggers = (
        "prove", "derive", "solve", "calculate",
        "theorem", "proof", "equation",
        "integral", "derivative",
        "math", "logic", "algebra", "geometry",
        "докажи", "реши", "найди", "уравнение"
    )

    return any(x in t for x in triggers)