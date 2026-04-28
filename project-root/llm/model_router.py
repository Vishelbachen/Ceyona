from contracts.shared_types import Tier

# ─── MODEL REGISTRY ──────────────────────────────────────────────────────────

_TIER_MODEL_MAP: dict[str, str] = {
    Tier.FAST:    "llama-3.1-8b-instant",
    Tier.GENERAL: "llama-3.3-70b-versatile",
    Tier.HEAVY:   "llama-3.3-70b-versatile",   # swap to gpt-oss-120b when available
}

# Max tokens per tier — matches policy_registry caps
_TIER_MAX_TOKENS: dict[str, int] = {
    Tier.FAST:    300,
    Tier.GENERAL: 1200,
    Tier.HEAVY:   3000,
}


def route_model(tier: Tier) -> str:
    """Return model identifier for a given tier."""
    return _TIER_MODEL_MAP[tier]


def route_max_tokens(tier: Tier) -> int:
    """Return max output tokens for a given tier."""
    return _TIER_MAX_TOKENS[tier]