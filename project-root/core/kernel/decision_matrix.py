from __future__ import annotations

from contracts.shared_types import Tier
from core.kernel.policy_registry import RUNTIME

# ─── TIER THRESHOLDS (USD) ────────────────────────────────────────────────
# Read from policy_registry.RUNTIME — single source of truth.
# Changing thresholds: edit policy_registry.py ONLY.
# Both values are auto-synced here — no manual synchronization needed.
#
# Synchronization contract (economic.md §6):
#   _FAST_CEILING    == RUNTIME.epk.fast_ceiling      (0.0005)
#   _GENERAL_CEILING == RUNTIME.epk.degrade_threshold (0.003)

_FAST_CEILING: float = RUNTIME.epk.fast_ceiling
_GENERAL_CEILING: float = RUNTIME.epk.degrade_threshold


def select_tier(estimated_cost: float) -> Tier:
    """
    Select execution tier based on estimated cost.

    Called by orchestrator ONLY after EPK returns ALLOW.
    HEAVY_REQUIRED and DEGRADED_MODE bypass this — tier is implicit in the EPK signal.
    NO policy authority. NO routing decisions.
    """
    if estimated_cost < _FAST_CEILING:
        return Tier.FAST
    if estimated_cost < _GENERAL_CEILING:
        return Tier.GENERAL
    return Tier.HEAVY


def tier_band(estimated_cost: float) -> str:
    """Return a human-readable label for the selected cost band."""
    tier = select_tier(estimated_cost)
    return tier.value