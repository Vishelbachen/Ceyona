def estimate_cost(intent: dict) -> float:

    if intent["type"] == "simple":
        return 0.0

    if intent["type"] == "reasoning":
        return 0.001

    if intent["type"] == "multi_agent":
        return 0.005

    return 0.01