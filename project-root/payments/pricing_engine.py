from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


# =========================
# MODEL TIERS (COST GROUPING)
# =========================
ModelTier = Literal["fast", "general", "heavy", "retrieval", "agent"]


@dataclass(frozen=True)
class CostProfile:
    """
    Defines abstract compute cost per operation unit.

    NOTE:
    This is NOT billing.
    This is internal cost modeling for control + limits.
    """
    per_request_cost: float
    llm_multiplier: float = 1.0
    retrieval_cost: float = 0.0
    agent_cost: float = 0.0


# =========================
# DEFAULT COST TABLE
# =========================
COST_TABLE: Dict[ModelTier, CostProfile] = {
    "fast": CostProfile(per_request_cost=1.0, llm_multiplier=0.5),
    "general": CostProfile(per_request_cost=2.0, llm_multiplier=1.0),
    "heavy": CostProfile(per_request_cost=5.0, llm_multiplier=2.5),
    "retrieval": CostProfile(per_request_cost=1.5, retrieval_cost=1.0),
    "agent": CostProfile(per_request_cost=3.0, agent_cost=2.0),
}


# =========================
# PRICING ENGINE
# =========================
class PricingEngine:
    """
    ROLE:
    - estimate compute cost BEFORE execution
    - normalize heterogeneous pipeline costs into unified units
    - support AccessController + future optimization layer

    DOES NOT:
    - enforce limits
    - block requests
    - make routing decisions
    """

    def estimate_request_cost(
        self,
        tier: ModelTier,
        *,
        use_retrieval: bool = False,
        use_agents: bool = False,
        llm_steps: int = 1,
    ) -> float:

        profile = COST_TABLE[tier]

        cost = profile.per_request_cost

        # LLM scaling
        cost *= profile.llm_multiplier * llm_steps

        # optional subsystems
        if use_retrieval:
            cost += profile.retrieval_cost

        if use_agents:
            cost += profile.agent_cost

        return cost

    # =========================
    # BATCH ESTIMATION
    # =========================
    def estimate_batch_cost(
        self,
        tier: ModelTier,
        batch_size: int,
        **kwargs,
    ) -> float:
        return self.estimate_request_cost(tier, **kwargs) * batch_size