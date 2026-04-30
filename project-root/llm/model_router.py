from contracts.shared_types import Tier

_TIER_MODEL_MAP: dict[str, str] = {
    Tier.FAST:    "llama-3.1-8b-instant",
    Tier.GENERAL: "llama-3.3-70b-versatile",   # умная модель
    Tier.HEAVY:   "llama-3.3-70b-versatile",
}

_TIER_MAX_TOKENS: dict[str, int] = {
    Tier.FAST:    512,     # подняли с 300
    Tier.GENERAL: 2048,    # подняли с 1200
    Tier.HEAVY:   4096,    # подняли с 3000
}


def route_model(tier: Tier) -> str:
    return _TIER_MODEL_MAP[tier]


def route_max_tokens(tier: Tier) -> int:
    return _TIER_MAX_TOKENS[tier]