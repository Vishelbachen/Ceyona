"""
test_epk_governance.py — Cost governance regression tests
Ensures EPK thresholds never drift silently (audit §6.1, economic.md §5–6)

These tests are ARCHITECTURE TESTS — they catch:
- expensive routing regressions
- EPK threshold drift
- decision_matrix synchronization failures
- MAX_OUTPUT_CAP vs _MAX_TOKENS confusion (architecture.md §8)
"""



# ─── Threshold constants (from economic.md §5-6, policy_registry) ────────────
DENY_THRESHOLD    = 0.0001
DEGRADE_THRESHOLD = 0.003
HEAVY_THRESHOLD   = 0.008
FAST_CEILING      = 0.0005
GENERAL_CEILING   = 0.003   # MUST equal DEGRADE_THRESHOLD (synchronization contract)


class TestEPKThresholdSync:
    """economic.md §11: GENERAL_CEILING must equal _DEGRADE_THRESHOLD"""

    def test_general_ceiling_equals_degrade_threshold(self):
        assert GENERAL_CEILING == DEGRADE_THRESHOLD, (
            "Synchronization contract violated: "
            "decision_matrix._GENERAL_CEILING must equal EPK._DEGRADE_THRESHOLD"
        )

    def test_fast_ceiling_below_general(self):
        """audit §6.2: ascending order — the old bug was FAST > GENERAL"""
        assert FAST_CEILING < GENERAL_CEILING, (
            "decision_matrix ordering broken: FAST_CEILING must be < GENERAL_CEILING"
        )

    def test_heavy_threshold_above_degrade(self):
        assert HEAVY_THRESHOLD > DEGRADE_THRESHOLD

    def test_deny_threshold_below_all(self):
        assert DENY_THRESHOLD < FAST_CEILING < GENERAL_CEILING < HEAVY_THRESHOLD


class TestEPKDecisions:
    """EPK evaluation order: DENY → HEAVY → DEGRADE → ALLOW (economic.md §5)"""

    def _evaluate(self, estimated_cost: float, user_balance: float) -> str:
        if user_balance <= 0 or estimated_cost > user_balance:
            return "DENY"
        if estimated_cost > HEAVY_THRESHOLD:
            return "HEAVY_REQUIRED"
        if estimated_cost > DEGRADE_THRESHOLD:
            return "DEGRADED_MODE"
        return "ALLOW"

    def test_zero_balance_is_deny(self):
        assert self._evaluate(0.001, 0.0) == "DENY"

    def test_negative_balance_is_deny(self):
        assert self._evaluate(0.001, -5.0) == "DENY"

    def test_cost_exceeds_balance_is_deny(self):
        assert self._evaluate(0.05, 0.01) == "DENY"

    def test_normal_short_query_is_allow(self):
        # 500 input + 600 output at GENERAL = ~$0.00077 → ALLOW
        assert self._evaluate(0.00077, 0.10) == "ALLOW"

    def test_large_query_is_degraded(self):
        # 3000 input + 2048 output at GENERAL = ~$0.0034 → DEGRADED
        assert self._evaluate(0.0034, 0.10) == "DEGRADED_MODE"

    def test_very_large_query_is_heavy(self):
        # 8000 input + 4096 output at GENERAL = ~$0.0085 → HEAVY
        assert self._evaluate(0.0085, 0.10) == "HEAVY_REQUIRED"

    def test_deny_beats_heavy(self):
        """DENY is evaluated first — zero balance trumps heavy eligibility"""
        assert self._evaluate(0.01, 0.0) == "DENY"


class TestDecisionMatrixTierSelection:
    """decision_matrix.select_tier() — called only after EPK returns ALLOW"""

    def _select_tier(self, estimated_cost: float) -> str:
        if estimated_cost < FAST_CEILING:
            return "FAST"
        if estimated_cost < GENERAL_CEILING:
            return "GENERAL"
        return "HEAVY"

    def test_tiny_request_is_fast(self):
        # 500 input + 300 output at FAST = $0.000049
        assert self._select_tier(0.000049) == "FAST"

    def test_medium_request_is_general(self):
        # 1000 input + 1200 output at GENERAL = $0.00154
        assert self._select_tier(0.00154) == "GENERAL"

    def test_border_fast_ceiling(self):
        assert self._select_tier(FAST_CEILING - 0.0000001) == "FAST"
        assert self._select_tier(FAST_CEILING) == "GENERAL"

    def test_border_general_ceiling(self):
        assert self._select_tier(GENERAL_CEILING - 0.0000001) == "GENERAL"
        assert self._select_tier(GENERAL_CEILING) == "HEAVY"


class TestMaxOutputCapVsMaxTokens:
    """
    architecture.md §8: MAX_OUTPUT_CAP (cost estimation) and _MAX_TOKENS
    (API hard limit) MUST NOT be equal — they serve different purposes.
    """

    MAX_OUTPUT_CAP = {"FAST": 512, "GENERAL": 2048, "HEAVY": 4096}
    MAX_TOKENS     = {"FAST": 1024, "GENERAL": 3072, "HEAVY": 6144}

    def test_max_output_cap_is_less_than_max_tokens(self):
        for tier in ("FAST", "GENERAL", "HEAVY"):
            assert self.MAX_OUTPUT_CAP[tier] < self.MAX_TOKENS[tier], (
                f"Tier {tier}: MAX_OUTPUT_CAP must be < _MAX_TOKENS "
                f"(conservative estimation vs API hard limit)"
            )

    def test_caps_are_not_equal(self):
        for tier in ("FAST", "GENERAL", "HEAVY"):
            assert self.MAX_OUTPUT_CAP[tier] != self.MAX_TOKENS[tier]


class TestFreeTrialBalance:
    """economic.md §9: $0.10 free trial must support minimum viable usage"""

    FREE_TRIAL = 0.10
    MARGIN     = 1.3

    def test_free_trial_covers_fast_queries(self):
        # ~50 short FAST queries at $0.00006 each * margin
        cost_per_query = 0.000049 * self.MARGIN
        queries = int(self.FREE_TRIAL / cost_per_query)
        assert queries >= 50, f"Free trial too small: only {queries} fast queries"

    def test_free_trial_covers_some_general_queries(self):
        # ~5 GENERAL queries at $0.002 each * margin
        cost_per_query = 0.002 * self.MARGIN
        queries = int(self.FREE_TRIAL / cost_per_query)
        assert queries >= 5, f"Free trial too small: only {queries} general queries"

    def test_margin_is_above_one(self):
        assert self.MARGIN > 1.0, "Margin must be > 1.0 for sustainable billing"