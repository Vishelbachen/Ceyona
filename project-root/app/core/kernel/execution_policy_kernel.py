from payments.pricing_engine import estimate_cost

def evaluate(intent: dict, balance: float = 0.0):

    cost = estimate_cost(intent)

    if balance < cost:
        return "DENY"

    if intent.get("risk_score", 0) > 0.8:
        return "DEGRADED_MODE"

    return "ALLOW"