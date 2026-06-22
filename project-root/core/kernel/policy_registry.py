from __future__ import annotations

from dataclasses import dataclass

from contracts.shared_types import Tier


@dataclass(frozen=True)
class TierConfig:
    """Runtime API limits per tier — matches model_router._MAX_TOKENS."""
    max_input_tokens: int    # context window safety limit
    max_output_tokens: int   # hard API limit passed to Groq
    timeout_seconds: float   # per-request timeout


@dataclass(frozen=True)
class EPKConfig:
    """EPK thresholds — MUST match execution_policy_kernel.py exactly."""
    deny_threshold: float    # balance ≤ 0 or cost > balance → DENY
    heavy_threshold: float   # cost > this → HEAVY_REQUIRED
    degrade_threshold: float # cost > this → DEGRADED_MODE (synced with decision_matrix._GENERAL_CEILING)
    fast_ceiling: float      # below this → FAST tier (synced with decision_matrix._FAST_CEILING)


@dataclass(frozen=True)
class RuntimePolicy:
    epk: EPKConfig
    tier_configs: dict[Tier, TierConfig]
    rate_limit_rpm: int        # requests per minute per user
    default_balance_usd: float  # free trial balance


# ─── ACTIVE RUNTIME POLICY ────────────────────────────────────────────────
# All values synchronized with:
#   economic.md v5.0 (EPK thresholds, balance)
#   model_router.py (max_output_tokens, timeouts)
# Last sync: May 2026

RUNTIME = RuntimePolicy(
    epk=EPKConfig(
        deny_threshold=0.0001,   # effectively zero — synced with EPK._DENY_THRESHOLD
        heavy_threshold=0.010,   # raised from 0.008: HEAVY request (3000in/7500out at $0.15/$0.60) = $0.005
                                  # headroom for large HEAVY requests before DENY kicks in
        degrade_threshold=0.006, # raised from 0.003: calibrated to qwen3.6-27b $3.00/output
                                  # normal GENERAL request (800in/900out) = (800×0.60+900×3.00)/1M = $0.003 → ALLOW
                                  # large GENERAL request (1500in/1500out) = (1500×0.60+1500×3.00)/1M = $0.005 → ALLOW
                                  # oversized request (2000in/2000out) = $0.007 → DEGRADED_MODE (correct)
        fast_ceiling=0.001,      # raised from 0.0005: FAST now $0.30/output (gpt-oss-20b)
                                  # short FAST request (500in/300out at $0.075/$0.30) = $0.000128 → FAST
                                  # medium FAST request (2000in/600out) = $0.000330 → FAST
                                  # at old $0.0005 ceiling, gpt-oss-20b requests were leaking to GENERAL
    ),
    tier_configs={
        Tier.FAST: TierConfig(
            max_input_tokens=8_192,   # conservative window limit
            max_output_tokens=1_024,  # matches model_router._MAX_TOKENS[Tier.FAST]
            timeout_seconds=15.0,
        ),
        Tier.GENERAL: TierConfig(
            max_input_tokens=32_768,  # conservative window limit (qwen3.6-27b Groq limit: 131K)
            max_output_tokens=3_072,  # matches model_router._MAX_TOKENS[Tier.GENERAL]
            timeout_seconds=45.0,
        ),
        Tier.HEAVY: TierConfig(
            max_input_tokens=131_072, # conservative window limit
            max_output_tokens=6_144,  # matches model_router._MAX_TOKENS[Tier.HEAVY]
            timeout_seconds=180.0,
        ),
    },
    rate_limit_rpm=30,
    default_balance_usd=0.10,  # matches access_controller._DEFAULT_BALANCE_USD
)


def get_tier_config(tier: Tier) -> TierConfig:
    """Return the runtime policy block for the requested tier."""
    return RUNTIME.tier_configs[tier]


def validate_runtime_policy() -> None:
    """Fail fast if the runtime policy drifts from the declared tiers."""
    required_tiers = {Tier.FAST, Tier.GENERAL, Tier.HEAVY}
    missing = required_tiers.difference(RUNTIME.tier_configs)
    if missing:
        missing_names = ", ".join(sorted(t.value for t in missing))
        raise ValueError(f"Missing tier configuration(s): {missing_names}")

    for tier, cfg in RUNTIME.tier_configs.items():
        if cfg.max_input_tokens <= 0:
            raise ValueError(f"{tier.value} max_input_tokens must be positive")
        if cfg.max_output_tokens <= 0:
            raise ValueError(f"{tier.value} max_output_tokens must be positive")
        if cfg.timeout_seconds <= 0:
            raise ValueError(f"{tier.value} timeout_seconds must be positive")


__all__ = [
    "TierConfig",
    "EPKConfig",
    "RuntimePolicy",
    "RUNTIME",
    "get_tier_config",
    "validate_runtime_policy",
]