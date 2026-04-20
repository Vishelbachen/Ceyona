from typing import Tuple, Dict, Any

from app.engine.intent_classifier import classify_intent
from app.core.types import IntentResult
from app.config.settings import settings


SHORT_TEXT = 50
MID_TEXT = 300


# -------------------------
# MAIN BRAIN ROUTER
# -------------------------
def resolve_model(text: str) -> Tuple[str, IntentResult, Dict[str, Any]]:

    text = text or ""
    text_len = len(text)

    intent_result = classify_intent(text)

    decision_meta = {
        "text_length": text_len,
        "intent": intent_result.intent,
        "task_type": intent_result.task_type,
        "complexity": intent_result.complexity,
        "confidence": intent_result.confidence,
        "route": None,
    }

    # -------------------------
    # SAFETY OVERRIDE
    # -------------------------
    if intent_result.is_high_risk():
        model = _pick("safety")
        decision_meta["route"] = "safety_override"
        return model, intent_result, decision_meta

    # -------------------------
    # TASK-BASED OVERRIDE (NEW)
    # -------------------------
    if intent_result.task_type == "coding":
        model = _pick("heavy")
        decision_meta["route"] = "task_coding"
        return model, intent_result, decision_meta

    if intent_result.task_type == "math_physics":
        model = _pick("heavy")
        decision_meta["route"] = "task_math"
        return model, intent_result, decision_meta

    # -------------------------
    # HIGH COMPLEXITY
    # -------------------------
    if intent_result.complexity == "high":
        model = _pick("heavy")
        decision_meta["route"] = "complexity_high"
        return model, intent_result, decision_meta

    # -------------------------
    # LOW CONFIDENCE
    # -------------------------
    if intent_result.confidence < 0.6:
        model = _size_based_model(text_len)
        decision_meta["route"] = "low_confidence_fallback"
        return model, intent_result, decision_meta

    # -------------------------
    # INTENT-BASED
    # -------------------------
    model = _select_by_intent(intent_result)

    if model:
        decision_meta["route"] = "intent_routing"
        return model, intent_result, decision_meta

    # -------------------------
    # FINAL FALLBACK
    # -------------------------
    model = _size_based_model(text_len)
    decision_meta["route"] = "final_fallback"

    return model, intent_result, decision_meta


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
# MODEL PICKER (SAFE)
# -------------------------
def _pick(layer: str) -> str:

    models = settings.MODEL_LAYERS.get(layer)

    if not models:
        # fallback to general layer
        models = settings.MODEL_LAYERS.get("general", [])

    return models[0] if models else ""


# -------------------------
# SIZE FALLBACK
# -------------------------
def _size_based_model(n: int) -> str:

    if n < SHORT_TEXT:
        return _pick("fast")

    if n < MID_TEXT:
        return _pick("general")

    return _pick("heavy")