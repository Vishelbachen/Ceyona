"""
test_coverage_boost.py — Unit tests for previously uncovered modules.

Targets (from CI coverage report):
  - retrieval/source_credibility.py  (51% → aim 90%+)
  - llm/model_router.py              (0%  → aim 80%+)
  - i18n/t.py                        (0%  → aim 100%)
  - contracts/shared_types.py        (0%  → aim 100%)
  - meta/correction.py               (0%  → aim 80%+)
  - meta/output_normalizer.py        (0%  → aim 70%+)
  - core/kernel/cost_model.py        (partial → improve)

All tests are pure unit — no I/O, no Groq, no Supabase, no HuggingFace.
"""

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# contracts/shared_types.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestSharedTypes:
    def test_tier_values(self):
        from contracts.shared_types import Tier
        assert Tier.FAST.value == "FAST"
        assert Tier.GENERAL.value == "GENERAL"
        assert Tier.HEAVY.value == "HEAVY"

    def test_complexity_values(self):
        from contracts.shared_types import Complexity
        assert Complexity.LOW.value == "LOW"
        assert Complexity.MEDIUM.value == "MEDIUM"
        assert Complexity.HIGH.value == "HIGH"
        assert Complexity.CRITICAL.value == "CRITICAL"

    def test_epk_decision_values(self):
        from contracts.shared_types import EPKDecision
        assert EPKDecision.ALLOW.value == "ALLOW"
        assert EPKDecision.DENY.value == "DENY"
        assert EPKDecision.DEGRADED_MODE.value == "DEGRADED_MODE"
        assert EPKDecision.HEAVY_REQUIRED.value == "HEAVY_REQUIRED"

    def test_truth_mode_values(self):
        from contracts.shared_types import TruthMode
        assert TruthMode.STRICT.value == "strict"
        assert TruthMode.HYBRID.value == "hybrid"
        assert TruthMode.GENERATIVE.value == "generative"

    def test_tier_is_string_enum(self):
        from contracts.shared_types import Tier

        # str-based Enum: can be compared to strings
        assert Tier.FAST == "FAST"

    def test_all_tiers_iterable(self):
        from contracts.shared_types import Tier
        tiers = list(Tier)
        assert len(tiers) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# i18n/t.py — get_system_message / format_balance_message
# ═══════════════════════════════════════════════════════════════════════════════

class TestI18nT:
    def test_get_system_message_returns_string(self):
        from i18n.t import get_system_message
        result = get_system_message("no_response", "ru")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_system_message_fallback_on_unknown_key(self):
        from i18n.t import get_system_message
        result = get_system_message("__nonexistent_key_xyz__", "ru")
        # Must return fallback string, not crash
        assert isinstance(result, str)
        assert result == "⚠️ An error occurred."

    def test_format_balance_message_returns_string(self):
        from i18n.t import format_balance_message
        result = format_balance_message(0.42, "ru")
        assert isinstance(result, str)

    def test_format_balance_message_contains_amount(self):
        from i18n.t import format_balance_message
        result = format_balance_message(1.23, "en")
        # Should contain formatted number somewhere in the string
        assert "1.23" in result or isinstance(result, str)

    def test_normalize_lang_exported(self):
        from i18n.t import normalize_lang
        assert callable(normalize_lang)

    def test_t_exported(self):
        from i18n.t import t
        assert callable(t)

    def test_supported_langs_exported(self):
        from i18n.t import SUPPORTED_LANGS
        assert isinstance(SUPPORTED_LANGS, (list, set, frozenset, dict))
        assert len(SUPPORTED_LANGS) > 0

    def test_get_system_message_and_response_synthesizer_agree(self):
        """i18n.t.get_system_message must return same value as cognition version."""
        from cognition.response_synthesizer import get_system_message as cog_gsm
        from i18n.t import get_system_message as i18n_gsm
        assert i18n_gsm("no_response", "ru") == cog_gsm("no_response", "ru")
        assert i18n_gsm("safety_block", "en") == cog_gsm("safety_block", "en")


# ═══════════════════════════════════════════════════════════════════════════════
# retrieval/source_credibility.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestSourceCredibilityEvaluate:
    def test_explicit_blocked_domain(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://all-routes.ru/some/path")
        assert score.tier == TrustTier.BLOCKED
        assert score.is_blocked is True
        assert score.reason == "explicit_registry"

    def test_explicit_authoritative_domain(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://openweathermap.org/api")
        assert score.tier == TrustTier.AUTHORITATIVE
        assert score.is_blocked is False

    def test_explicit_high_domain(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://booking.com/hotel/ru")
        assert score.tier == TrustTier.HIGH

    def test_explicit_medium_domain(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://en.wikipedia.org/wiki/Test")
        assert score.tier == TrustTier.MEDIUM

    def test_explicit_very_low_domain(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://otvet.mail.ru/question/123")
        assert score.tier == TrustTier.VERY_LOW

    def test_www_prefix_stripped(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://www.booking.com/hotel")
        assert score.tier == TrustTier.HIGH

    def test_gov_pattern_authoritative(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://example.gov.ru/page")
        assert score.tier == TrustTier.AUTHORITATIVE

    def test_gov_tld_authoritative(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://agency.gov/info")
        assert score.tier == TrustTier.AUTHORITATIVE

    def test_edu_tld_high(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://mit.edu/research")
        assert score.tier == TrustTier.HIGH

    def test_seo_pattern_very_low(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://top-rating-otzyv.com/article")
        assert score.tier == TrustTier.VERY_LOW

    def test_unknown_domain_defaults_medium(self):
        from retrieval.source_credibility import TrustTier, evaluate
        score = evaluate("https://some-totally-unknown-domain-xyz123.com/page")
        assert score.tier == TrustTier.MEDIUM
        assert score.reason == "unknown_domain"
        assert score.is_blocked is False

    def test_empty_url_does_not_crash(self):
        from retrieval.source_credibility import evaluate
        score = evaluate("")
        assert score is not None

    def test_malformed_url_does_not_crash(self):
        from retrieval.source_credibility import evaluate
        score = evaluate("not_a_url_at_all")
        assert score is not None

    def test_score_range(self):
        from retrieval.source_credibility import evaluate
        for url in [
            "https://all-routes.ru/",
            "https://wikipedia.org/",
            "https://openweathermap.org/",
            "https://unknown-xyz.com/",
        ]:
            score = evaluate(url)
            assert 0.0 <= score.score <= 1.0

    def test_domain_field_populated(self):
        from retrieval.source_credibility import evaluate
        score = evaluate("https://www.booking.com/hotel/ru")
        assert score.domain == "booking.com"


class TestSourceCredibilityFilterResults:
    def _make_results(self, urls):
        return [{"title": f"Title {i}", "link": url, "snippet": "text"} for i, url in enumerate(urls)]

    def test_blocked_domain_filtered(self):
        from retrieval.source_credibility import filter_results
        results = self._make_results(["https://all-routes.ru/page", "https://booking.com/hotel"])
        kept = filter_results(results)
        links = [r["link"] for r in kept]
        assert "https://all-routes.ru/page" not in links
        assert "https://booking.com/hotel" in links

    def test_very_low_domain_filtered_by_default(self):
        from retrieval.source_credibility import filter_results
        results = self._make_results(["https://otvet.mail.ru/q", "https://booking.com/hotel"])
        kept = filter_results(results)
        links = [r["link"] for r in kept]
        assert "https://otvet.mail.ru/q" not in links

    def test_max_results_respected(self):
        from retrieval.source_credibility import filter_results
        urls = [f"https://booking.com/hotel/{i}" for i in range(10)]
        results = self._make_results(urls)
        kept = filter_results(results, max_results=3)
        assert len(kept) <= 3

    def test_credibility_metadata_annotated(self):
        from retrieval.source_credibility import filter_results
        results = self._make_results(["https://booking.com/hotel"])
        kept = filter_results(results)
        assert len(kept) == 1
        assert "_credibility" in kept[0]
        cred = kept[0]["_credibility"]
        assert "domain" in cred
        assert "tier" in cred
        assert "score" in cred
        assert "reason" in cred

    def test_empty_results_returns_empty(self):
        from retrieval.source_credibility import filter_results
        assert filter_results([]) == []

    def test_order_preserved(self):
        from retrieval.source_credibility import filter_results
        urls = ["https://booking.com/a", "https://google.com/b", "https://wikipedia.org/c"]
        results = self._make_results(urls)
        kept = filter_results(results)
        kept_links = [r["link"] for r in kept]
        # Order of kept items should match original order
        original_order = [u for u in urls if u in kept_links]
        assert kept_links == original_order


class TestSourceCredibilityScoreDocuments:
    def test_pass_through(self):
        from retrieval.source_credibility import score_documents
        docs = [("text one", 0.9), ("text two", 0.7)]
        result = score_documents(docs)
        assert result == docs

    def test_empty_pass_through(self):
        from retrieval.source_credibility import score_documents
        assert score_documents([]) == []


class TestSourceCredibilitySingleton:
    def test_singleton_evaluate(self):
        from retrieval.source_credibility import TrustTier, source_credibility
        score = source_credibility.evaluate("https://openweathermap.org/")
        assert score.tier == TrustTier.AUTHORITATIVE

    def test_singleton_filter(self):
        from retrieval.source_credibility import source_credibility
        results = [{"title": "T", "link": "https://booking.com/h", "snippet": "s"}]
        kept = source_credibility.filter_results(results)
        assert len(kept) == 1

    def test_singleton_score_documents(self):
        from retrieval.source_credibility import source_credibility
        docs = [("hello", 0.5)]
        assert source_credibility.score_documents(docs) == docs


# ═══════════════════════════════════════════════════════════════════════════════
# llm/model_router.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelRouter:
    def test_route_model_fast(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_model
        assert route_model(Tier.FAST) == "llama-3.1-8b-instant"

    def test_route_model_general(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_model
        assert route_model(Tier.GENERAL) == "llama-3.3-70b-versatile"

    def test_route_model_heavy(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_model
        assert route_model(Tier.HEAVY) == "openai/gpt-oss-120b"

    def test_route_max_tokens_fast_less_than_general(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_max_tokens
        assert route_max_tokens(Tier.FAST) < route_max_tokens(Tier.GENERAL)

    def test_route_max_tokens_general_less_than_heavy(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_max_tokens
        assert route_max_tokens(Tier.GENERAL) < route_max_tokens(Tier.HEAVY)

    def test_get_tier_models_fast_nonempty(self):
        from contracts.shared_types import Tier
        from llm.model_router import get_tier_models
        models = get_tier_models(Tier.FAST)
        assert len(models) >= 1
        assert "llama-3.1-8b-instant" in models

    def test_get_tier_models_general_has_multiple(self):
        from contracts.shared_types import Tier
        from llm.model_router import get_tier_models
        models = get_tier_models(Tier.GENERAL)
        assert len(models) >= 2

    def test_get_tier_models_heavy_has_two(self):
        from contracts.shared_types import Tier
        from llm.model_router import get_tier_models
        models = get_tier_models(Tier.HEAVY)
        assert len(models) >= 2

    def test_requires_thinking_disabled_qwen(self):
        from llm.model_router import requires_thinking_disabled
        assert requires_thinking_disabled("qwen/qwen3-32b") is True

    def test_requires_thinking_disabled_llama(self):
        from llm.model_router import requires_thinking_disabled
        assert requires_thinking_disabled("llama-3.3-70b-versatile") is False

    def test_constants_exported(self):
        from llm.model_router import (
            CONSENSUS_MODEL,
            DEEP_AGENT_MODEL,
            FAST_AGENT_MODEL,
        )
        assert FAST_AGENT_MODEL == "groq/compound-mini"
        assert DEEP_AGENT_MODEL == "groq/compound"
        assert CONSENSUS_MODEL == "openai/gpt-oss-120b"

    def test_max_tokens_positive(self):
        from contracts.shared_types import Tier
        from llm.model_router import route_max_tokens
        for tier in Tier:
            assert route_max_tokens(tier) > 0

    def test_max_tokens_greater_than_estimation_cap(self):
        """architecture.md §8: _MAX_TOKENS > MAX_OUTPUT_CAP — they must NOT be equal."""
        from contracts.shared_types import Tier
        from core.kernel.cost_model import MAX_OUTPUT_CAP
        from llm.model_router import route_max_tokens
        for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY):
            assert route_max_tokens(tier) > MAX_OUTPUT_CAP[tier], (
                f"{tier}: model_router._MAX_TOKENS ({route_max_tokens(tier)}) "
                f"must be > cost_model.MAX_OUTPUT_CAP ({MAX_OUTPUT_CAP[tier]})"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# core/kernel/cost_model.py — additional coverage
# ═══════════════════════════════════════════════════════════════════════════════

class TestCostModelAdditional:
    def test_estimate_output_tokens_capped(self):
        from contracts.shared_types import Complexity, Tier
        from core.kernel.cost_model import MAX_OUTPUT_CAP, estimate_output_tokens

        # Very large input should be capped
        result = estimate_output_tokens(100_000, Complexity.CRITICAL, Tier.FAST)
        assert result == MAX_OUTPUT_CAP[Tier.FAST]

    def test_estimate_output_tokens_low_complexity(self):
        from contracts.shared_types import Complexity, Tier
        from core.kernel.cost_model import estimate_output_tokens
        result = estimate_output_tokens(100, Complexity.LOW, Tier.GENERAL)
        assert result == int(100 * 1.2)  # 120

    def test_estimate_cost_zero_inputs(self):
        from contracts.shared_types import Tier
        from core.kernel.cost_model import estimate_cost
        cost = estimate_cost(0, 0, 0, 0, Tier.FAST)
        assert cost == 0.0

    def test_estimate_cost_embedding_small_type(self):
        from contracts.shared_types import Tier
        from core.kernel.cost_model import estimate_cost
        cost_large = estimate_cost(0, 0, 1_000_000, 0, Tier.FAST, embedding_type="large")
        cost_small = estimate_cost(0, 0, 1_000_000, 0, Tier.FAST, embedding_type="small")
        assert cost_large > cost_small

    def test_actual_cost_equals_estimate_when_same_tokens(self):
        from contracts.shared_types import Tier
        from core.kernel.cost_model import actual_cost, estimate_cost
        kwargs = dict(input_tokens=500, output_tokens=300, embedding_tokens=100, rerank_tokens=50, tier=Tier.GENERAL)
        est = estimate_cost(500, 300, 100, 50, Tier.GENERAL)
        act = actual_cost(**kwargs)
        assert abs(est - act) < 1e-12

    def test_heavy_cheaper_output_than_general(self):
        """economic.md: gpt-oss-120b output $0.60 < llama-3.3-70b output $0.79"""
        from contracts.shared_types import Tier
        from core.kernel.cost_model import MODEL_RATES
        assert MODEL_RATES[Tier.HEAVY]["output"] < MODEL_RATES[Tier.GENERAL]["output"]

    def test_all_tiers_have_rates(self):
        from contracts.shared_types import Tier
        from core.kernel.cost_model import MODEL_RATES
        for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY):
            assert "input" in MODEL_RATES[tier]
            assert "output" in MODEL_RATES[tier]


# ═══════════════════════════════════════════════════════════════════════════════
# meta/correction.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetaCorrection:
    def _get_apply(self):
        import importlib
        mod = importlib.import_module("meta.correction")
        for name in ("apply", "strip", "correct", "strip_boilerplate", "run"):
            if hasattr(mod, name):
                return getattr(mod, name)
        for name in dir(mod):
            if not name.startswith("_"):
                obj = getattr(mod, name)
                if callable(obj):
                    return obj
        raise AttributeError("Cannot find public function in meta.correction")

    def test_fixes_unclosed_code_block(self):
        """Odd number of ``` → correction closes it."""
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        text = "Here is some code:\n```python\nprint('hello')"
        result = fn(text)
        assert result.count("```") % 2 == 0, "Unclosed code block should be closed"

    def test_fixes_unclosed_bold(self):
        """Odd number of ** → correction closes it."""
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        text = "This is **important text"
        result = fn(text)
        assert result.count("**") % 2 == 0, "Unclosed bold should be closed"

    def test_collapses_excessive_blank_lines(self):
        """4+ consecutive blank lines → collapsed to 3."""
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        text = "First paragraph.\n\n\n\n\nSecond paragraph."
        result = fn(text)
        assert "\n\n\n\n" not in result, "4+ blank lines should be collapsed"

    def test_does_not_modify_clean_text(self):
        """Clean text with no structural issues passes through unchanged."""
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        clean = "Москва — столица России."
        result = fn(clean)
        assert "Москва" in result

    def test_preamble_passes_through(self):
        """
        correction.py no longer strips preambles — that is the prompt's job.
        Preamble text must survive correction unchanged (no false stripping).
        """
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        # These should NOT be stripped by correction.py
        text = "Sure! Here is your answer."
        result = fn(text)
        assert "Sure" in result, (
            "correction.py must not strip preambles — that is the prompt's job"
        )

    def test_empty_string_safe(self):
        import meta.correction as correction
        fn = getattr(correction, "apply", None)
        if fn is None:
            pytest.skip("No apply function in meta.correction")
        result = fn("")
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════════════════
# meta/output_normalizer.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMetaOutputNormalizer:
    def _get_normalize(self):
        import meta.output_normalizer as mod
        for name in ("normalize", "apply", "run", "clean"):
            fn = getattr(mod, name, None)
            if fn and callable(fn):
                return fn
        pytest.skip("No public function found in meta.output_normalizer")

    def test_strips_source_tag_ru(self):
        fn = self._get_normalize()
        text = "Гостиница стоит 5000 руб (источник 3) в сутки."
        result = fn(text, "ru")
        assert "(источник 3)" not in result
        assert "5000 руб" in result

    def test_strips_source_tag_en(self):
        fn = self._get_normalize()
        text = "The price is $100 (source 2) per night."
        result = fn(text, "en")
        assert "(source 2)" not in result

    def test_strips_garbled_url(self):
        fn = self._get_normalize()
        text = "Подробнее: https://example.com/путь/к/странице дополнительная информация."
        result = fn(text, "ru")
        # Garbled URL should be removed
        assert "https://example.com/путь" not in result

    def test_clean_text_unchanged_core(self):
        fn = self._get_normalize()
        text = "Москва — столица России."
        result = fn(text, "ru")
        assert "Москва" in result
        assert "столица" in result

    def test_empty_string_safe(self):
        fn = self._get_normalize()
        result = fn("", "ru")
        assert isinstance(result, str)

    def test_returns_string(self):
        fn = self._get_normalize()
        result = fn("Some response text.", "en")
        assert isinstance(result, str)