from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal


# =========================
# MODEL TIERS (PURE LLM COST GROUPS)
# =========================
ModelTier = Literal["fast", "general", "heavy"]


# =========================
# SUBSYSTEM FLAGS
# =========================
@dataclass(frozen=True)
class SubsystemCost:
    retrieval: float = 0.0
    agent: float = 0.0


# =========================
# BASE COST PROFILE
# =========================
@dataclass(frozen=True)
class CostProfile:
    """
    Pure compute cost model.

    ROLE:
    - estimate relative system load
    - normalize heterogeneous pipeline costs

    DOES NOT:
    - enforce billing
    - influence routing
    - block execution
    """

    base_cost: float
    llm_multiplier: float = 1.0
    subsystem: SubsystemCost = SubsystemCost()


# =========================
# COST TABLE (CLEAN SEPARATION)
# =========================
COST_TABLE: Dict[ModelTier, CostProfile] = {
    "fast": CostProfile(base_cost=1.0, llm_multiplier=0.5),
    "general": CostProfile(base_cost=2.0, llm_multiplier=1.0),
    "heavy": CostProfile(base_cost=5.0, llm_multiplier=2.5),
}


# =========================
# PRICING ENGINE
# =========================
class PricingEngine:
    """
    ROLE:
    - deterministic cost estimation
    - unified compute abstraction layer
    - pre-execution cost projection

    DOES NOT:
    - enforce limits
    - make routing decisions
    - influence EPK or agents
    """

    # =========================
    # SINGLE REQUEST COST
    # =========================
    def estimate_request_cost(
        self,
        tier: ModelTier,
        *,
        use_retrieval: bool = False,
        use_agents: bool = False,
        llm_steps: int = 1,
    ) -> float:

        profile = COST_TABLE[tier]

        # base LLM cost
        cost = profile.base_cost * profile.llm_multiplier * llm_steps

        # subsystem costs (additive, deterministic)
        if use_retrieval:
            cost += profile.subsystem.retrieval

        if use_agents:
            cost += profile.subsystem.agent

        return cost

    # =========================
    # BATCH COST
    # =========================
    def estimate_batch_cost(
        self,
        tier: ModelTier,
        batch_size: int,
        **kwargs,
    ) -> float:

        return self.estimate_request_cost(tier, **kwargs) * batch_size