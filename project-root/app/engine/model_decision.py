from app.engine.intent_classifier import classify_intent, IntentResult
from app.config.settings import settings

SHORT_TEXT = 50
MID_TEXT = 300


def resolve_model(text: str) -> tuple[str, IntentResult]:
    text = text or ""
    text_len = len(text)

    intent_result = classify_intent(text)

    # HARD OVERRIDE: reasoning
    if _is_reasoning_heavy(text):
        return settings.HEAVY_MODELS[0], intent_result

    # LOW RELIABILITY
    if _is_low_reliability(intent_result, text_len):
        return _size_based_model(text_len), intent_result

    # POLICY ROUTING
    model = _select_by_intent(intent_result)
    if model:
        return model, intent_result

    # FALLBACK
    return _size_based_model(text_len), intent_result


def _select_by_intent(intent: IntentResult) -> str:
    mapping = {
        "fast": settings.FAST_MODELS,
        "chat": settings.GENERAL_MODELS,
        "reasoning": settings.HEAVY_MODELS,
        "creative": settings.GENERAL_MODELS,
        "safety": settings.SAFETY_MODELS,
    }
    return mapping.get(intent.intent, settings.GENERAL_MODELS)[0]


def _size_based_model(n: int) -> str:
    if n < SHORT_TEXT:
        return settings.FAST_MODELS[0]
    if n < MID_TEXT:
        return settings.GENERAL_MODELS[0]
    return settings.HEAVY_MODELS[0]


def _is_low_reliability(intent: IntentResult, n: int) -> bool:
    if n < 20:
        return True

    if intent.intent not in {"fast", "chat", "reasoning", "creative", "safety"}:
        return True

    return False


def _is_reasoning_heavy(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in [
        "prove", "derive", "solve", "equation",
        "integral", "theorem", "calculate",
        "докажи", "реши", "уравнение"
    ])