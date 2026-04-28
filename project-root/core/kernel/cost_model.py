from dataclasses import dataclass
from typing import Dict, Any

from app.settings import Settings


@dataclass
class CostEstimate:
    """
    Structured cost output for execution planning.
    """
    input_cost: float
    output_cost: float
    total_cost: float
    tier: str


class CostModel:
    """
    AI Platform v4.7 — Cost Model Engine

    RESPONSIBILITY:
    - Calculate deterministic cost estimates
    - Based on MODEL_RATES (FAST / GENERAL / HEAVY)
    - Provide pricing signal for EPK

    STRICT RULES:
    - No routing decisions
    - No execution control
    - No LLM calls
    - No retrieval / memory access
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        # v4.7 single source of truth rates
        self.rates = {
            "FAST": {"input": 0.25, "output": 0.9},
            "GENERAL": {"input": 2.5, "output": 10},
            "HEAVY": {"input": 8, "output": 30},
        }

    def estimate(self, tier: str, input_tokens: int, output_tokens: int) -> CostEstimate:
        """
        Deterministic cost calculation.
        """

        if tier not in self.rates:
            raise ValueError(f"Invalid tier: {tier}")

        rate = self.rates[tier]

        input_cost = (input_tokens / 1_000_000) * rate["input"]
        output_cost = (output_tokens / 1_000_000) * rate["output"]

        total_cost = input_cost + output_cost

        return CostEstimate(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            tier=tier,
        )

    def estimate_from_payload(self, tier: str, payload: Dict[str, Any]) -> CostEstimate:
        """
        Convenience wrapper using heuristic token estimation.
        """

        text = payload.get("text", "") or ""

        # deterministic token approximation (no NLP)
        input_tokens = max(1, len(text) // 4)
        output_tokens = self.settings.MAX_TOKENS_FAST if tier == "FAST" else (
            self.settings.MAX_TOKENS_GENERAL if tier == "GENERAL" else self.settings.MAX_TOKENS_HEAVY
        )

        return self.estimate(
            tier=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )