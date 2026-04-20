from app.config.settings import settings
from app.engine.types import IntentResult


# -------------------------
# SIMPLE ROUND-ROBIN STATE (IN-MEMORY)
# -------------------------
_MODEL_INDEX = {
    "fast": 0,
    "general": 0,
    "heavy": 0,
    "safety": 0
}


def _pick_model(models: list[str], layer: str) -> str:
    """
    Simple rotation (prevents always picking first model)
    """
    global _MODEL_INDEX

    if not models:
        return ""

    idx = _MODEL_INDEX[layer] % len(models)
    _MODEL_INDEX[layer] += 1

    return models[idx]


# -------------------------
# MAIN ROUTER
# -------------------------
def select_model_by_intent(intent: IntentResult) -> str:

    layer = "general"

    # -------------------------
    # MAP INTENT → LAYER
    # -------------------------
    if intent.intent == "safety":
        layer = "safety"

    elif intent.intent == "reasoning":
        layer = "heavy"

    elif intent.intent == "creative":
        layer = "general"

    elif intent.intent == "fast":
        layer = "fast"

    # -------------------------
    # COMPLEXITY OVERRIDE (IMPORTANT)
    # -------------------------
    if intent.complexity == "high" and intent.intent != "safety":
        layer = "heavy"

    if intent.complexity == "low" and intent.intent == "fast":
        layer = "fast"

    # -------------------------
    # GET MODELS FROM SETTINGS
    # -------------------------
    models = settings.MODEL_LAYERS.get(layer, settings.MODEL_LAYERS["general"])

    return _pick_model(models, layer)