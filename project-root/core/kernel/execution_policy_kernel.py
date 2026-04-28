from dataclasses import dataclass

from contracts.shared_types import EPKDecision

# ─── POLICY THRESHOLDS ───────────────────────────────────────────────────────

_DENY_THRESHOLD: float = 0.0       # cost > balance → DENY
_DEGRADE_THRESHOLD: float = 0.30   # cost > 0.30 USD → DEGRADE


# ─── INPUT / OUTPUT CONTRACTS ────────────────────────────────────────────────

@dataclass(frozen=True)
class EPKInput:
    estimated_cost: float   # USD, from cost_model.estimate_cost()
    user_balance: float     # USD, from access_controller


@dataclass(frozen=True)
class EPKOutput:
    decision: EPKDecision
    reason: str


# ─── POLICY FUNCTION ─────────────────────────────────────────────────────────

def evaluate(epk_input: EPKInput) -> EPKOutput:
    """
    Pure stateless policy evaluation.
    Called by orchestrator before any execution begins.
    """
    cost = epk_input.estimated_cost
    balance = epk_input.user_balance

    if cost > balance:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    if cost > _DEGRADE_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DEGRADE,
            reason=f"Cost {cost:.6f} exceeds degrade threshold {_DEGRADE_THRESHOLD}",
        )

    return EPKOutput(
        decision=EPKDecision.ALLOW,
        reason="OK",
    )