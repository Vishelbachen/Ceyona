from contracts.shared_types import Tier

# ─── TIER THRESHOLDS (USD) ───────────────────────────────────────────────────

_FAST_CEILING: float = 0.05
_GENERAL_CEILING: float = 0.30


def select_tier(estimated_cost: float) -> Tier:
    """
    Select execution tier based on estimated cost.
    Called by orchestrator after EPK returns ALLOW or DEGRADE.
    """
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    elif estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    else:
        return Tier.HEAVY