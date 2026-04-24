from payments.pricing import estimate_cost

def evaluate(intent: dict, balance: float = 0.0) -> str:

    cost = estimate_cost(intent)

    if balance < cost:
        return "DENY"

    if intent.get("risk") == "high":
        return "DEGRADED_MODE"

    return "ALLOW"