"""
Tests for core/kernel/ — Sealed layer.
Covers: policy_registry, execution_policy_kernel, decision_matrix, cost_model.

These are the most critical tests in the suite.
A regression here means the billing and access control policy is broken.
"""

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.kernel.cost_model import (
    MAX_OUTPUT_CAP,
    MODEL_RATES,
    actual_cost,
    estimate_cost,
    estimate_output_tokens,
)
from core.kernel.decision_matrix import _FAST_CEILING, _GENERAL_CEILING, select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from core.kernel.policy_registry import RUNTIME

# ─── policy_registry ──────────────────────────────────────────────────────────

class TestPolicyRegistry:
    def test_runtime_exists(self):
        assert RUNTIME is not None

    def test_epk_thresholds_ordered(self):
        """DENY < DEGRADE < HEAVY — must be strictly ascending."""
        epk = RUNTIME.epk
        assert epk.deny_threshold < epk.degrade_threshold < epk.heavy_threshold

    def test_fast_ceiling_below_degrade(self):
        """fast_ceiling must be below degrade_threshold (tier selection sanity)."""
        assert RUNTIME.epk.fast_ceiling < RUNTIME.epk.degrade_threshold

    def test_tier_configs_present(self):
        for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY):
            assert tier in RUNTIME.tier_configs

    def test_tier_output_tokens_ascending(self):
        """FAST < GENERAL < HEAVY output caps."""
        fast    = RUNTIME.tier_configs[Tier.FAST].max_output_tokens
        general = RUNTIME.tier_configs[Tier.GENERAL].max_output_tokens
        heavy   = RUNTIME.tier_configs[Tier.HEAVY].max_output_tokens
        assert fast < general < heavy

    def test_default_balance_positive(self):
        assert RUNTIME.default_balance_usd > 0

    def test_rate_limit_positive(self):
        assert RUNTIME.rate_limit_rpm > 0


# ─── execution_policy_kernel ──────────────────────────────────────────────────

class TestEPK:
    """
    EPK rules (in order):
      1. balance <= 0 OR cost > balance → DENY
      2. cost > HEAVY_THRESHOLD         → HEAVY_REQUIRED
      3. cost > DEGRADE_THRESHOLD       → DEGRADED_MODE
      4. otherwise                      → ALLOW
    """

    def _inp(self, cost: float, balance: float) -> EPKInput:
        return EPKInput(estimated_cost=cost, user_balance=balance)

    # ── DENY ──────────────────────────────────────────────────────────────────

    def test_deny_zero_balance(self):
        result = evaluate(self._inp(cost=0.0001, balance=0.0))
        assert result.decision == EPKDecision.DENY

    def test_deny_negative_balance(self):
        result = evaluate(self._inp(cost=0.0001, balance=-1.0))
        assert result.decision == EPKDecision.DENY

    def test_deny_cost_exceeds_balance(self):
        result = evaluate(self._inp(cost=0.50, balance=0.10))
        assert result.decision == EPKDecision.DENY

    def test_deny_exact_cost_equals_balance(self):
        """cost > balance → DENY. cost == balance is NOT denied (edge case)."""
        balance = 0.005
        result = evaluate(self._inp(cost=balance, balance=balance))
        # cost == balance: NOT cost > balance → should not DENY on this rule
        # but may still be HEAVY/DEGRADE depending on thresholds
        assert result.decision != EPKDecision.DENY

    # ── HEAVY_REQUIRED ────────────────────────────────────────────────────────

    def test_heavy_required(self):
        cost = RUNTIME.epk.heavy_threshold + 0.001
        balance = cost * 10  # enough balance
        result = evaluate(self._inp(cost=cost, balance=balance))
        assert result.decision == EPKDecision.HEAVY_REQUIRED

    def test_heavy_not_triggered_at_degrade_level(self):
        cost = RUNTIME.epk.degrade_threshold + 0.0001
        balance = cost * 10
        result = evaluate(self._inp(cost=cost, balance=balance))
        assert result.decision == EPKDecision.DEGRADED_MODE

    # ── DEGRADED_MODE ─────────────────────────────────────────────────────────

    def test_degraded_mode(self):
        cost = RUNTIME.epk.degrade_threshold + 0.0001
        balance = cost * 10
        result = evaluate(self._inp(cost=cost, balance=balance))
        assert result.decision == EPKDecision.DEGRADED_MODE

    # ── ALLOW ─────────────────────────────────────────────────────────────────

    def test_allow_typical_fast_request(self):
        """Typical short message: ~300 input tokens, FAST tier → cost ~$0.00002."""
        cost = 0.00002
        result = evaluate(self._inp(cost=cost, balance=10.0))
        assert result.decision == EPKDecision.ALLOW

    def test_allow_typical_general_request(self):
        """Typical chat: ~500 input / 900 output, GENERAL → cost ~$0.001."""
        cost = 0.001
        result = evaluate(self._inp(cost=cost, balance=10.0))
        assert result.decision == EPKDecision.ALLOW

    # ── rule ordering ─────────────────────────────────────────────────────────

    def test_deny_takes_priority_over_heavy(self):
        """If cost > balance AND cost > heavy_threshold → DENY (rule 1 first)."""
        cost    = RUNTIME.epk.heavy_threshold + 0.01
        balance = 0.001  # cost > balance
        result  = evaluate(self._inp(cost=cost, balance=balance))
        assert result.decision == EPKDecision.DENY

    def test_result_has_reason(self):
        result = evaluate(self._inp(cost=0.001, balance=0.0))
        assert result.reason != ""


# ─── decision_matrix ──────────────────────────────────────────────────────────

class TestDecisionMatrix:
    def test_fast_ceiling_synced_with_policy_registry(self):
        assert _FAST_CEILING == RUNTIME.epk.fast_ceiling

    def test_general_ceiling_synced_with_policy_registry(self):
        assert _GENERAL_CEILING == RUNTIME.epk.degrade_threshold

    def test_ascending_order(self):
        """Critical: _FAST_CEILING < _GENERAL_CEILING or GENERAL tier is unreachable."""
        assert _FAST_CEILING < _GENERAL_CEILING

    def test_select_tier_fast(self):
        cost = _FAST_CEILING * 0.5
        assert select_tier(cost) == Tier.FAST

    def test_select_tier_general(self):
        cost = _FAST_CEILING + (_GENERAL_CEILING - _FAST_CEILING) / 2
        assert select_tier(cost) == Tier.GENERAL

    def test_select_tier_heavy(self):
        cost = _GENERAL_CEILING + 0.001
        assert select_tier(cost) == Tier.HEAVY

    def test_select_tier_exactly_at_fast_ceiling(self):
        """At exactly fast_ceiling: cost < _FAST_CEILING is False → GENERAL."""
        assert select_tier(_FAST_CEILING) == Tier.GENERAL

    def test_select_tier_exactly_at_general_ceiling(self):
        """At exactly general_ceiling: cost < _GENERAL_CEILING is False → HEAVY."""
        assert select_tier(_GENERAL_CEILING) == Tier.HEAVY


# ─── cost_model ───────────────────────────────────────────────────────────────

class TestCostModel:
    def test_model_rates_all_tiers_present(self):
        for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY):
            assert tier in MODEL_RATES
            assert "input" in MODEL_RATES[tier]
            assert "output" in MODEL_RATES[tier]

    def test_model_rates_positive(self):
        for tier, rates in MODEL_RATES.items():
            assert rates["input"] > 0, f"{tier} input rate must be positive"
            assert rates["output"] > 0, f"{tier} output rate must be positive"

    def test_max_output_cap_ascending(self):
        assert MAX_OUTPUT_CAP[Tier.FAST] < MAX_OUTPUT_CAP[Tier.GENERAL] < MAX_OUTPUT_CAP[Tier.HEAVY]

    def test_estimate_output_tokens_capped(self):
        """Even huge input should not exceed MAX_OUTPUT_CAP."""
        for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY):
            result = estimate_output_tokens(100_000, Complexity.CRITICAL, tier)
            assert result <= MAX_OUTPUT_CAP[tier]

    def test_estimate_output_tokens_scales_with_complexity(self):
        low  = estimate_output_tokens(500, Complexity.LOW,      Tier.GENERAL)
        high = estimate_output_tokens(500, Complexity.CRITICAL, Tier.GENERAL)
        assert low < high

    def test_estimate_cost_positive(self):
        cost = estimate_cost(
            input_tokens=500,
            estimated_output_tokens=900,
            embedding_tokens=0,
            rerank_tokens=0,
            tier=Tier.GENERAL,
        )
        assert cost > 0

    def test_estimate_cost_zero_tokens(self):
        cost = estimate_cost(0, 0, 0, 0, Tier.FAST)
        assert cost == 0.0

    def test_actual_vs_estimate_same_formula(self):
        """actual_cost and estimate_cost use the same formula — results should match
        when given identical token counts."""
        kwargs = dict(
            input_tokens=500,
            embedding_tokens=100,
            rerank_tokens=50,
            tier=Tier.GENERAL,
            embedding_type="large",
        )
        estimated = estimate_cost(estimated_output_tokens=900, **kwargs)
        actual    = actual_cost(output_tokens=900, **kwargs)
        assert abs(estimated - actual) < 1e-9

    def test_typical_fast_request_cheap(self):
        """300 input / 200 output on FAST tier should cost < $0.0001."""
        cost = actual_cost(300, 200, 0, 0, Tier.FAST)
        assert cost < 0.0001

    def test_typical_general_request_below_degrade_threshold(self):
        """500 input / 900 output on GENERAL should be below DEGRADE threshold ($0.003)."""
        cost = actual_cost(500, 900, 0, 0, Tier.GENERAL)
        assert cost < RUNTIME.epk.degrade_threshold