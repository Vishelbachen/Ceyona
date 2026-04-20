from app.engine.intent_classifier import classify_intent, IntentResult
from app.config.settings import settings


SHORT_TEXT = 50
MID_TEXT = 300


# -------------------------
# MAIN BRAIN ROUTER
# -------------------------
def resolve_model(text: str) -> tuple[str, IntentResult]:

    text = text or ""

    intent_result = classify_intent(text)
    text_len = len(text)

    # -------------------------
    # SAFETY OVERRIDE (highest priority)
    # -------------------------
    if intent_result.intent == "safety":
        return _pick("safety"), intent_result

    # -------------------------
    # HIGH COMPLEXITY → HEAVY
    # -------------------------
    if intent_result.complexity == "high":
        return _pick("heavy"), intent_result

    # -------------------------
    # LOW CONFIDENCE → CONSERVATIVE ROUTING
    # -------------------------
    if intent_result.confidence < 0.6:
        return _size_based_model(text_len), intent_result

    # -------------------------
    # INTENT-BASED ROUTING
    # -------------------------
    model = _select_by_intent(intent_result)

    if model:
        return model, intent_result

    # -------------------------
    # FINAL FALLBACK
    # -------------------------
    return _size_based_model(text_len), intent_result


# -------------------------
# INTENT → LAYER
# -------------------------
def _select_by_intent(intent: IntentResult) -> str:

    layer_map = {
        "fast": "fast",
        "chat": "general",
        "reasoning": "heavy",
        "creative": "general",
        "safety": "safety",
    }

    layer = layer_map.get(intent.intent, "general")

    return _pick(layer)


# -------------------------
# MODEL PICKER (FIXED)
# -------------------------
def _pick(layer: str) -> str:

    models = settings.MODEL_LAYERS.get(layer, settings.MODEL_LAYERS["general"])

    # simple rotation-safe fallback
    return models[0] if models else ""


# -------------------------
# SIZE FALLBACK (SAFE ONLY)
# -------------------------
def _size_based_model(n: int) -> str:

    if n < SHORT_TEXT:
        return _pick("fast")

    if n < MID_TEXT:
        return _pick("general")

    return _pick("heavy")