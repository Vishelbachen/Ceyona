from typing import Dict, Any


class PricingEngine:
    """
    AI Platform v4.7 — Pricing Engine

    RESPONSIBILITY:
    - Calculate cost of usage based on MODEL_RATES
    - Provide pricing signals for access_controller
    - Support tier-based pricing logic

    STRICT RULES:
    - No access control decisions
    - No payment execution
    - No blockchain interaction
    - No LLM / retrieval / memory usage
    """

    def __init__(self):
        # single source of truth (aligned with system spec)
        self.rates = {
            "FAST": {"input": 0.25, "output": 0.9},
            "GENERAL": {"input": 2.5, "output": 10},
            "HEAVY": {"input": 8.0, "output": 30.0},
        }

    def estimate_cost(
        self,
        tier: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Dict[str, float]:
        """
        Deterministic cost calculation per request.
        """

        if tier not in self.rates:
            raise ValueError(f"Invalid tier: {tier}")

        rate = self.rates[tier]

        input_cost = (input_tokens / 1_000_000) * rate["input"]
        output_cost = (output_tokens / 1_000_000) * rate["output"]

        total_cost = input_cost + output_cost

        return {
            "tier": tier,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    def estimate_from_text(self, tier: str, text: str) -> Dict[str, float]:
        """
        Lightweight heuristic token approximation.
        """

        input_tokens = max(1, len(text) // 4)

        # deterministic assumption (no model inference)
        if tier == "FAST":
            output_tokens = 300
        elif tier == "GENERAL":
            output_tokens = 1200
        else:
            output_tokens = 3000

        return self.estimate_cost(
            tier=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )