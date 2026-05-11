from dataclasses import dataclass
from contracts.shared_types import EPKDecision

# ─── THRESHOLDS ───────────────────────────────────────────────────────────────
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

_DENY_THRESHOLD:    float = 0.0001   # effectively zero balance check
_HEAVY_THRESHOLD:   float = 0.008    # large multi-step tasks → gpt-oss-120b
_DEGRADE_THRESHOLD: float = 0.003    # oversized requests → FAST only


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