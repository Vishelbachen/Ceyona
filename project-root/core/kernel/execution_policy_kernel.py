from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


# =========================
# DECISION TYPES
# =========================
Decision = Literal["ALLOW", "DENY", "DEGRADED_MODE"]


# =========================
# CONTEXT INPUT
# =========================
@dataclass(frozen=True)
class ExecutionContext:
    user_id: str
    plan: str
    estimated_cost: float
    usage_day_limit: int
    usage_month_limit: int
    remaining_day: int
    remaining_month: int
    system_load: float  # 0.0 - 1.0
    risk_flag: bool = False


# =========================
# OUTPUT
# =========================
@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    metadata: Optional[Dict[str, Any]] = None


# =========================
# EXECUTION POLICY KERNEL (EPK)
# =========================
class ExecutionPolicyKernel:
    """
    ROLE:
    - deterministic policy evaluation layer
    - decides ALLOW / DENY / DEGRADED_MODE

    STRICT RULES:
    - NO I/O
    - NO MEMORY ACCESS
    - NO LLM ACCESS
    - NO SIDE EFFECTS
    - NO BUSINESS LOGIC BEYOND POLICY
    """

    # =========================
    # MAIN POLICY FUNCTION
    # =========================
    def evaluate(self, ctx: ExecutionContext) -> PolicyDecision:

        # 1. HARD SAFETY GATE
        if ctx.risk_flag:
            return PolicyDecision(
                decision="DENY",
                reason="risk_flag_triggered",
            )

        # 2. HARD LIMIT CHECKS
        if ctx.remaining_day <= 0:
            return PolicyDecision(
                decision="DENY",
                reason="daily_limit_exceeded",
            )

        if ctx.remaining_month <= 0:
            return PolicyDecision(
                decision="DENY",
                reason="monthly_limit_exceeded",
            )

        # 3. COST GUARD (soft enforcement via degradation)
        if ctx.estimated_cost > 10.0:
            return PolicyDecision(
                decision="DEGRADED_MODE",
                reason="high_cost_request",
                metadata={
                    "suggested_action": "use_fast_model_or_reduce_steps"
                },
            )

        # 4. SYSTEM LOAD PROTECTION
        if ctx.system_load > 0.85:
            return PolicyDecision(
                decision="DEGRADED_MODE",
                reason="high_system_load",
            )

        # 5. NORMAL PATH
        return PolicyDecision(
            decision="ALLOW",
            reason="ok",
        )