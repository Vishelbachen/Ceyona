from contracts.shared_types import Tier

_TIER_MODEL_MAP: dict[str, str] = {
    Tier.FAST:    "llama-3.1-8b-instant",
    Tier.GENERAL: "llama-3.3-70b-versatile",
    Tier.HEAVY:   "openai/gpt-oss-120b",
}

_TIER_MAX_TOKENS: dict[str, int] = {
    Tier.FAST:    512,
    Tier.GENERAL: 2048,
    Tier.HEAVY:   4096,
}


def route_model(tier: Tier) -> str:
    return _TIER_MODEL_MAP[tier]


def route_max_tokens(tier: Tier) -> int:
    return _TIER_MAX_TOKENS[tier]