from contracts.shared_types import Tier

# ─── TIER THRESHOLDS (USD) ───────────────────────────────────────────────────

_FAST_CEILING:    float = 0.05
_GENERAL_CEILING: float = 0.003  # synced with EPK _DEGRADE_THRESHOLD


def select_tier(estimated_cost: float) -> Tier:
    """
    Select execution tier based on estimated cost.
    Called by orchestrator ONLY after EPK returns ALLOW.
    HEAVY_REQUIRED and DEGRADED_MODE bypass this — tier is implicit in EPK signal.
    NO policy authority. NO routing decisions.
    """
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    if estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    return Tier.HEAVY