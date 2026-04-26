from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# =========================
# COST BUCKETS
# =========================
CostBucket = Literal["low", "medium", "high"]


# =========================
# COST INPUT
# =========================
@dataclass(frozen=True)
class CostFactors:
    """
    Structural inputs for compute cost estimation.
    """

    tokens_estimate: int
    model_tier: str
    use_retrieval: bool = False
    use_agents: bool = False
    llm_steps: int = 1


# =========================
# COST OUTPUT
# =========================
@dataclass(frozen=True)
class CostEstimate:
    raw_cost: float
    bucket: CostBucket


# =========================
# COST MODEL
# =========================
class CostModel:
    """
    ROLE:
    - deterministic compute cost estimation
    - bucket classification for policy layer (EPK / DecisionMatrix)

    STRICT RULES:
    - no access control
    - no payment logic
    - no user state
    - no LLM calls
    """

    # =========================
    # BASE WEIGHTS (STATIC)
    # =========================
    _tier_weights = {
        "fast": 1.0,
        "general": 2.0,
        "heavy": 5.0,
        "retrieval": 1.5,
        "agent": 3.0,
    }

    _token_cost_factor = 0.0001

    # =========================
    # MAIN ESTIMATION
    # =========================
    def estimate(self, f: CostFactors) -> CostEstimate:

        tier_weight = self._tier_weights.get(f.model_tier, 2.0)

        # base compute cost
        cost = (
            f.tokens_estimate * self._token_cost_factor * tier_weight * f.llm_steps
        )

        # subsystem multipliers
        if f.use_retrieval:
            cost += 1.0

        if f.use_agents:
            cost += 2.0

        return CostEstimate(
            raw_cost=cost,
            bucket=self._bucket(cost),
        )

    # =========================
    # BUCKETIZATION
    # =========================
    def _bucket(self, cost: float) -> CostBucket:

        if cost < 1.0:
            return "low"

        if cost < 5.0:
            return "medium"

        return "high"