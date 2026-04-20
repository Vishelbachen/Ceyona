from typing import List, Dict

from app.config.settings import settings


# -------------------------
# ROUND-ROBIN STATE
# -------------------------
_MODEL_INDEX: Dict[str, int] = {
    "fast": 0,
    "general": 0,
    "heavy": 0,
    "safety": 0
}


# -------------------------
# SAFE MODEL PICK
# -------------------------
def pick_model_from_layer(layer: str) -> str:
    """
    Select model from a given layer using round-robin strategy.
    This is a POLICY layer — does NOT decide the layer.
    """

    models = _get_models(layer)

    if not models:
        return ""

    idx = _next_index(layer, len(models))
    return models[idx]


# -------------------------
# INTERNAL: GET MODELS
# -------------------------
def _get_models(layer: str) -> List[str]:

    models = settings.MODEL_LAYERS.get(layer)

    if not models:
        # fallback to general
        models = settings.MODEL_LAYERS.get("general", [])

    return models or []


# -------------------------
# INTERNAL: SAFE ROTATION
# -------------------------
def _next_index(layer: str, size: int) -> int:
    """
    Safe rotation counter.
    """

    if size <= 0:
        return 0

    current = _MODEL_INDEX.get(layer, 0)

    idx = current % size

    _MODEL_INDEX[layer] = current + 1

    return idx