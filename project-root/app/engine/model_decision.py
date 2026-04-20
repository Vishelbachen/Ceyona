from app.engine.intent_classifier import classify_intent
from app.engine.model_policy import select_model_by_intent
from app.config.settings import settings
from app.engine.types import IntentResult

SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:

    text = text or ""
    text_len = len(text)

    # 1. intent detection
    intent_result: IntentResult = classify_intent(text)

    # 2. hard reasoning override
    if _is_reasoning_heavy(text):
        return settings.HEAVY_MODELS[0], intent_result

    # 3. weak signal fallback
    if _is_low_reliability(intent_result, text_len):
        return _size_based_model(text_len), intent_result

    # 4. policy routing
    try:
        model = select_model_by_intent(intent_result)
        if model:
            return model, intent_result
    except Exception:
        pass

    # 5. deterministic fallback
    return _size_based_model(text_len), intent_result


# -------------------------
# HELPERS
# -------------------------

def _size_based_model(text_len: int) -> str:

    if text_len < SHORT_TEXT:
        return settings.FAST_MODELS[0]

    if text_len < MID_TEXT:
        return settings.GENERAL_MODELS[0]

    return settings.HEAVY_MODELS[0]


def _is_low_reliability(intent_result: IntentResult, text_len: int) -> bool:

    if text_len < 20:
        return True

    return intent_result.intent is None


def _is_reasoning_heavy(text: str) -> bool:

    t = text.lower()

    triggers = (
        "prove", "derive", "solve", "calculate",
        "equation", "theorem", "proof",
        "integral", "derivative",
        "докажи", "реши", "уравнение"
    )

    return any(x in t for x in triggers)