from dataclasses import dataclass
from contracts.shared_types import EPKDecision

# ─── THRESHOLDS ───────────────────────────────────────────────────────────────

_DENY_THRESHOLD:    float = 0.001   # balance ≤ 0 or cost > balance → DENY
_HEAVY_THRESHOLD:   float = 0.30    # cost > 0.30 AND balance sufficient → HEAVY_REQUIRED
_DEGRADE_THRESHOLD: float = 0.10    # cost > 0.10 AND balance sufficient → DEGRADED_MODE


@dataclass(frozen=True)
class EPKInput:
    estimated_cost: float
    user_balance: float


@dataclass(frozen=True)
class EPKOutput:
    decision: EPKDecision
    reason: str


def evaluate(epk_input: EPKInput) -> EPKOutput:
    """
    SOLE POLICY AUTHORITY.
    OUTPUT: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED

    Rules (evaluated in order):
      1. balance ≤ 0 or cost > balance → DENY
      2. cost > HEAVY_THRESHOLD        → HEAVY_REQUIRED
      3. cost > DEGRADE_THRESHOLD      → DEGRADED_MODE
      4. otherwise                     → ALLOW
    """
    cost    = epk_input.estimated_cost
    balance = epk_input.user_balance

    # ── 1. DENY ───────────────────────────────────────────────────────────────
    if balance <= 0 or cost > balance:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    # ── 2. HEAVY_REQUIRED ─────────────────────────────────────────────────────
    if cost > _HEAVY_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.HEAVY_REQUIRED,
            reason=f"Cost {cost:.6f} exceeds heavy threshold {_HEAVY_THRESHOLD}",
        )

    # ── 3. DEGRADED_MODE ──────────────────────────────────────────────────────
    if cost > _DEGRADE_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DEGRADED_MODE,
            reason=f"Cost {cost:.6f} exceeds degrade threshold {_DEGRADE_THRESHOLD}",
        )

    # ── 4. ALLOW ──────────────────────────────────────────────────────────────
    return EPKOutput(decision=EPKDecision.ALLOW, reason="OK")