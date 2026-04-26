from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Tuple


Decision = Literal["ALLOW", "DENY", "DEGRADED_MODE"]


# =========================
# DECISION INPUT KEYS
# =========================
@dataclass(frozen=True)
class DecisionFactors:
    """
    Pure structural input vector for policy evaluation.
    """

    cost_bucket: str        # "low" | "medium" | "high"
    system_load: str        # "low" | "medium" | "high"
    user_tier: str         # "free" | "pro" | "premium"
    risk_level: str        # "safe" | "suspicious" | "risky"


# =========================
# DECISION MATRIX
# =========================
class DecisionMatrix:
    """
    ROLE:
    - deterministic rule table for execution decisions
    - used by EPK or orchestrator

    STRICT RULES:
    - no runtime state
    - no ML / heuristics
    - no external dependencies
    """

    def __init__(self):

        # (cost, load, risk, tier) → decision
        self._matrix: Dict[Tuple[str, str, str, str], Decision] = {

            # SAFE ZONES
            ("low", "low", "safe", "free"): "ALLOW",
            ("low", "low", "safe", "pro"): "ALLOW",
            ("low", "low", "safe", "premium"): "ALLOW",

            ("medium", "low", "safe", "free"): "DEGRADED_MODE",
            ("medium", "low", "safe", "pro"): "ALLOW",
            ("medium", "low", "safe", "premium"): "ALLOW",

            ("high", "low", "safe", "premium"): "DEGRADED_MODE",
            ("high", "low", "safe", "pro"): "DENY",
            ("high", "low", "safe", "free"): "DENY",

            # LOAD STRESS
            ("low", "high", "safe", "premium"): "DEGRADED_MODE",
            ("medium", "high", "safe", "pro"): "DEGRADED_MODE",
            ("high", "high", "safe", "free"): "DENY",

            # RISK OVERRIDE (HARD BLOCK)
            ("low", "low", "risky", "free"): "DENY",
            ("low", "medium", "risky", "pro"): "DENY",
            ("medium", "medium", "risky", "premium"): "DENY",

            # SUSPICIOUS → degraded only
            ("low", "low", "suspicious", "free"): "DEGRADED_MODE",
            ("medium", "low", "suspicious", "pro"): "DEGRADED_MODE",
            ("high", "low", "suspicious", "premium"): "DEGRADED_MODE",
        }

    # =========================
    # RESOLVE DECISION
    # =========================
    def resolve(self, factors: DecisionFactors) -> Decision:

        key = (
            factors.cost_bucket,
            factors.system_load,
            factors.risk_level,
            factors.user_tier,
        )

        # strict lookup
        if key in self._matrix:
            return self._matrix[key]

        # fallback rules (deterministic safety default)
        if factors.risk_level == "risky":
            return "DENY"

        if factors.system_load == "high":
            return "DEGRADED_MODE"

        if factors.cost_bucket == "high":
            return "DEGRADED_MODE"

        return "ALLOW"