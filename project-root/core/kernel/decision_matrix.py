from contracts.shared_types import Tier

# ─── TIER THRESHOLDS (USD) ───────────────────────────────────────────────────

# ASCENDING ORDER IS MANDATORY.
# Previous values (0.05 / 0.003) were inverted — GENERAL tier was unreachable.
# Fixed in economic.md v5.0.
_FAST_CEILING:    float = 0.0005  # below $0.0005 → FAST  (~≤5000 combined tokens at FAST rates)
_GENERAL_CEILING: float = 0.003   # below $0.003  → GENERAL (synced with EPK _DEGRADE_THRESHOLD)


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