from dataclasses import dataclass
from contracts.shared_types import EPKDecision

_DENY_THRESHOLD: float = 0.001    # меньше $0.001 → DENY
_DEGRADE_THRESHOLD: float = 0.30  # больше $0.30 → DEGRADE


@dataclass(frozen=True)
class EPKInput:
    estimated_cost: float
    user_balance: float


@dataclass(frozen=True)
class EPKOutput:
    decision: EPKDecision
    reason: str


def evaluate(epk_input: EPKInput) -> EPKOutput:
    cost = epk_input.estimated_cost
    balance = epk_input.user_balance

    # нет баланса совсем
    if balance <= 0 and cost > _DENY_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    # баланс есть но не хватает
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

    return EPKOutput(decision=EPKDecision.ALLOW, reason="OK")