def estimate_cost(intent: dict) -> float:

    if not isinstance(intent, dict):
        return 0.01

    intent_type = intent.get("type", "default")

    if intent_type == "simple":
        return 0.0

    if intent_type == "reasoning":
        return 0.001

    if intent_type == "multi_agent":
        return 0.005

    return 0.01