from dataclasses import dataclass

from contracts.shared_types import Tier


@dataclass(frozen=True)
class TierConfig:
    """Runtime API limits per tier — matches model_router._MAX_TOKENS."""
    max_input_tokens:  int    # context window safety limit
    max_output_tokens: int    # hard API limit passed to Groq
    timeout_seconds:   float  # per-request timeout


@dataclass(frozen=True)
class EPKConfig:
    """EPK thresholds — MUST match execution_policy_kernel.py exactly."""
    deny_threshold:   float   # balance ≤ 0 or cost > balance → DENY
    heavy_threshold:  float   # cost > this → HEAVY_REQUIRED
    degrade_threshold: float  # cost > this → DEGRADED_MODE


@dataclass(frozen=True)
class RuntimePolicy:
    epk:          EPKConfig
    tier_configs: dict[str, TierConfig]
    rate_limit_rpm: int       # requests per minute per user
    default_balance_usd: float  # free trial balance


# ─── ACTIVE RUNTIME POLICY ────────────────────────────────────────────────────
# All values synchronized with:
#   economic.md v5.0 (EPK thresholds, balance)
#   model_router.py (max_output_tokens, timeouts)
# Last sync: May 2026

RUNTIME = RuntimePolicy(
    epk=EPKConfig(
        deny_threshold=0.0001,   # effectively zero — synced with EPK._DENY_THRESHOLD
        heavy_threshold=0.008,   # synced with EPK._HEAVY_THRESHOLD
        degrade_threshold=0.003, # synced with EPK._DEGRADE_THRESHOLD and decision_matrix._GENERAL_CEILING
    ),
    tier_configs={
        Tier.FAST: TierConfig(
            max_input_tokens=8_192,   # conservative window limit
            max_output_tokens=1_024,  # matches model_router._MAX_TOKENS[Tier.FAST]
            timeout_seconds=15.0,
        ),
        Tier.GENERAL: TierConfig(
            max_input_tokens=32_768,  # conservative window limit
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