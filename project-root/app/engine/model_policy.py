from app.config.settings import settings
from app.engine.types import IntentResult


def select_model_by_intent(intent: IntentResult) -> str:
    """
    Maps IntentResult → model group
    """

    match intent.intent:
        case "safety":
            return settings.SAFETY_MODELS[0]

        case "reasoning":
            return settings.HEAVY_MODELS[0]

        case "creative":
            return settings.GENERAL_MODELS[0]

        case "fast":
            return settings.FAST_MODELS[0]

        case _:
            return settings.GENERAL_MODELS[0]