from __future__ import annotations

from dataclasses import dataclass

from contracts.shared_types import EPKDecision
from core.kernel.policy_registry import RUNTIME

# ─── THRESHOLDS ───────────────────────────────────────────────────────────
# Read from policy_registry.RUNTIME — single source of truth.
# economic.md §5 defines the values; policy_registry.py holds them at runtime.
#
# Calibrated to ACTUAL Groq prices (May 2026):
#   FAST    llama-3.1-8b-instant:    $0.05 / $0.08  per 1M
#   GENERAL llama-3.3-70b-versatile: $0.59 / $0.79  per 1M
#   HEAVY   openai/gpt-oss-120b:     $0.15 / $0.60  per 1M
#
# Typical GENERAL request (500 in / 900 out) costs ~$0.001
# Typical HEAVY   request (3000 in / 7500 out) costs ~$0.005
#
# DENY:    balance ≤ 0 OR cost > balance
# DEGRADE: cost > $0.003  (≈ ~2000 input token GENERAL request)
# HEAVY:   cost > $0.008  (≈ ~5000 input token GENERAL / 3000 HEAVY request)
# ALLOW:   otherwise

_DENY_THRESHOLD: float = RUNTIME.epk.deny_threshold
_HEAVY_THRESHOLD: float = RUNTIME.epk.heavy_threshold
_DEGRADE_THRESHOLD: float = RUNTIME.epk.degrade_threshold


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
    Sole policy authority for execution gating.

    OUTPUT: ALLOW | DENY | DEGRADED_MODE | HEAVY_REQUIRED

    Thresholds are read from policy_registry.RUNTIME — do not hardcode here.

    Rules (evaluated in order):
      1. balance ≤ 0 or cost > balance → DENY
      2. cost > HEAVY_THRESHOLD        → HEAVY_REQUIRED
      3. cost > DEGRADE_THRESHOLD      → DEGRADED_MODE
      4. otherwise                     → ALLOW
    """
    cost = epk_input.estimated_cost
    balance = epk_input.user_balance

    if balance <= 0 or cost > balance:
        return EPKOutput(
            decision=EPKDecision.DENY,
            reason=f"Insufficient balance: need {cost:.6f}, have {balance:.6f}",
        )

    if cost > _HEAVY_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.HEAVY_REQUIRED,
            reason=f"Cost {cost:.6f} exceeds heavy threshold {_HEAVY_THRESHOLD}",
        )

    if cost > _DEGRADE_THRESHOLD:
        return EPKOutput(
            decision=EPKDecision.DEGRADED_MODE,
            reason=f"Cost {cost:.6f} exceeds degrade threshold {_DEGRADE_THRESHOLD}",
        )

    return EPKOutput(decision=EPKDecision.ALLOW, reason="OK")