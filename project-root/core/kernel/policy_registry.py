from dataclasses import dataclass
from contracts.shared_types import Tier


@dataclass(frozen=True)
class TierPolicy:
    max_input_tokens: int
    max_output_tokens: int
    timeout_seconds: float


@dataclass(frozen=True)
class PolicyRegistry:
    # EPK thresholds
    degrade_threshold_usd: float
    deny_above_balance: bool

    # Tier policies
    tier_policies: dict[str, TierPolicy]

    # Rate limiting (requests per minute per user)
    rate_limit_rpm: int


# ─── ACTIVE POLICY (v4.7) ────────────────────────────────────────────────────

ACTIVE_POLICY = PolicyRegistry(
    degrade_threshold_usd=0.30,
    deny_above_balance=True,

    tier_policies={
        Tier.FAST: TierPolicy(
            max_input_tokens=4_096,
            max_output_tokens=300,
            timeout_seconds=10.0,
        ),
        Tier.GENERAL: TierPolicy(
            max_input_tokens=16_384,
            max_output_tokens=1_200,
            timeout_seconds=30.0,
        ),
        Tier.HEAVY: TierPolicy(
            max_input_tokens=65_536,
            max_output_tokens=3_000,
            timeout_seconds=120.0,
        ),
    },

    rate_limit_rpm=30,
)