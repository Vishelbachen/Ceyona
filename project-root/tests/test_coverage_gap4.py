"""
test_coverage_gap4.py

Fourth coverage boost — target: total ≥ 75 %.

Targets (all pure unit — no real I/O):
  meta/reflection.py                    79 % → 100 %   (+24 stmts)
  retrieval/retrieval_models.py          0 % → 100 %   (+12 stmts)
  observability/tracing.py             41 % → 100 %   (+20 stmts)
  observability/metrics.py             73 % → 100 %   (+3  stmts)
  scripts/check_imports.py              0 % → ~90 %    (+41 stmts)
  notifications/event_notifier.py       0 % → ~90 %   (+15 stmts)
  payments/wallet_manager.py            0 % → ~85 %   (+43 stmts)
  agents/compound_agent.py              ? % → ~90 %   (+~25 stmts)
  llm/prompt_engine.py                  ? % → ~90 %   (+~20 stmts)
  webhook._get_chat_id/_detect_lang     ? % → ~80 %   (+~25 stmts)
  security/auth.py                      0 % → 100 %   (+13 stmts)
  security/origin_guard.py              0 % → 100 %   (+8  stmts)

No imports from app.settings at module level in this file.
Settings-dependent modules are patched at the boundary inside each test.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# retrieval/retrieval_models.py  (0 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalModels:
    def test_query_vector_fields(self):
        from retrieval.retrieval_models import QueryVector
        qv = QueryVector(text="hello", embedding=[0.1, 0.2], model="bge-large")
        assert qv.text == "hello"
        assert qv.embedding == [0.1, 0.2]
        assert qv.model == "bge-large"

    def test_query_vector_frozen(self):
        from retrieval.retrieval_models import QueryVector
        qv = QueryVector(text="x", embedding=[], model="m")
        with pytest.raises((AttributeError, TypeError)):
            qv.text = "y"  # type: ignore[misc]

    def test_scored_candidate_defaults(self):
        from retrieval.retrieval_models import ScoredCandidate
        sc = ScoredCandidate(content="result", score=0.95)
        assert sc.content == "result"
        assert sc.score == pytest.approx(0.95)
        assert sc.source == ""
        assert sc.metadata == {}

    def test_scored_candidate_with_source(self):
        from retrieval.retrieval_models import ScoredCandidate
        sc = ScoredCandidate(content="c", score=0.5, source="wiki", metadata={"k": "v"})
        assert sc.source == "wiki"
        assert sc.metadata == {"k": "v"}

    def test_scored_candidate_frozen(self):
        from retrieval.retrieval_models import ScoredCandidate
        sc = ScoredCandidate(content="c", score=0.1)
        with pytest.raises((AttributeError, TypeError)):
            sc.score = 1.0  # type: ignore[misc]

    def test_metadata_default_factory_independent(self):
        """Each instance gets its own dict — default_factory, not shared mutable."""
        from retrieval.retrieval_models import ScoredCandidate
        a = ScoredCandidate(content="a", score=0.1)
        b = ScoredCandidate(content="b", score=0.2)
        assert a.metadata is not b.metadata


# ══════════════════════════════════════════════════════════════════════════════
# observability/metrics.py  (73 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestMetrics:
    def setup_method(self):
        """Reset module-level state before each test."""
        import observability.metrics as m
        m._counters.clear()
        m._gauges.clear()

    def test_increment_default(self):
        from observability.metrics import increment, snapshot
        increment("req_count")
        snap = snapshot()
        assert snap["counters"]["req_count"] == 1

    def test_increment_custom_value(self):
        from observability.metrics import increment, snapshot
        increment("tokens", 100)
        snap = snapshot()
        assert snap["counters"]["tokens"] == 100

    def test_increment_accumulates(self):
        from observability.metrics import increment, snapshot
        increment("x")
        increment("x")
        increment("x", 3)
        assert snapshot()["counters"]["x"] == 5

    def test_gauge(self):
        from observability.metrics import gauge, snapshot
        gauge("latency_ms", 42.5)
        snap = snapshot()
        assert snap["gauges"]["latency_ms"] == pytest.approx(42.5)

    def test_gauge_overwrites(self):
        from observability.metrics import gauge, snapshot
        gauge("g", 1.0)
        gauge("g", 9.9)
        assert snapshot()["gauges"]["g"] == pytest.approx(9.9)

    def test_snapshot_returns_copy(self):
        from observability.metrics import increment, snapshot
        increment("a")
        s1 = snapshot()
        increment("a")
        s2 = snapshot()
        assert s1["counters"]["a"] == 1
        assert s2["counters"]["a"] == 2

    def test_snapshot_empty(self):
        from observability.metrics import snapshot
        snap = snapshot()
        assert snap["counters"] == {}
        assert snap["gauges"] == {}


# ══════════════════════════════════════════════════════════════════════════════
# observability/tracing.py  (41 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestTracing:
    def test_current_trace_id_none_outside_span(self):
        from observability.tracing import current_trace_id

        # Between tests there should be no active trace
        assert current_trace_id() is None

    def test_trace_sets_and_clears_trace_id(self):
        from observability.tracing import current_trace_id, trace
        assert current_trace_id() is None
        with trace("test_span"):
            assert current_trace_id() is not None
        assert current_trace_id() is None

    def test_trace_id_consistent_within_span(self):
        from observability.tracing import current_trace_id, trace
        ids = []
        with trace("outer"):
            ids.append(current_trace_id())
            ids.append(current_trace_id())
        assert ids[0] == ids[1]
        assert ids[0] is not None

    def test_nested_spans_share_trace_id(self):
        from observability.tracing import current_trace_id, trace
        outer_id = None
        inner_id = None
        with trace("outer"):
            outer_id = current_trace_id()
            with trace("inner"):
                inner_id = current_trace_id()
        assert outer_id == inner_id

    def test_trace_id_restored_after_nested(self):
        from observability.tracing import current_trace_id, trace
        with trace("outer"):
            outer_id = current_trace_id()
            with trace("inner"):
                pass
            assert current_trace_id() == outer_id

    def test_trace_propagates_exception(self):
        from observability.tracing import trace
        with pytest.raises(ValueError):
            with trace("failing_span"):
                raise ValueError("boom")

    def test_trace_clears_after_exception(self):
        from observability.tracing import current_trace_id, trace
        try:
            with trace("ex_span"):
                raise RuntimeError("oops")
        except RuntimeError:
            pass
        assert current_trace_id() is None

    def test_trace_emits_log_record(self):
        from observability.tracing import trace
        with patch("observability.tracing.logger") as mock_log:
            with trace("logged_span", tier="FAST"):
                pass
            mock_log.info.assert_called_once()
            call_kwargs = mock_log.info.call_args
            assert call_kwargs[0][0] == "trace"
            extra = call_kwargs[1]["extra"]
            assert "span_json" in extra

    def test_trace_tags_appear_in_log(self):
        import json

        from observability.tracing import trace
        with patch("observability.tracing.logger") as mock_log:
            with trace("tagged", intent="search", lang="ru"):
                pass
            extra = mock_log.info.call_args[1]["extra"]
            span = json.loads(extra["span_json"])
            assert span["intent"] == "search"
            assert span["lang"] == "ru"
            assert span["status"] == "ok"
            assert "elapsed_ms" in span

    def test_trace_status_error_on_exception(self):
        import json

        from observability.tracing import trace
        with patch("observability.tracing.logger") as mock_log:
            try:
                with trace("err_span"):
                    raise ValueError("x")
            except ValueError:
                pass
            extra = mock_log.info.call_args[1]["extra"]
            span = json.loads(extra["span_json"])
            assert span["status"] == "error"

    def test_sequential_spans_get_different_trace_ids(self):
        from observability.tracing import current_trace_id, trace
        id1 = id2 = None
        with trace("s1"):
            id1 = current_trace_id()
        with trace("s2"):
            id2 = current_trace_id()
        assert id1 != id2


# ══════════════════════════════════════════════════════════════════════════════
# meta/reflection.py  (79 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

def _make_input(**kwargs):
    from meta.reflection import ReflectionInput
    defaults = dict(
        intent="search", lang="ru", tier="GENERAL", model="llama-3.3-70b",
        response_text="Вот результат.", response_truncated=False, llm_cost_usd=0.001,
    )
    defaults.update(kwargs)
    return ReflectionInput(**defaults)


class TestReflectionSignals:
    def test_response_ok_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(response_text="Normal answer"))
        assert QualitySignal.RESPONSE_OK in r.signals

    def test_response_empty_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(response_text=""))
        assert QualitySignal.RESPONSE_EMPTY in r.signals
        assert QualitySignal.RESPONSE_OK not in r.signals

    def test_response_whitespace_only_is_empty(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(response_text="   "))
        assert QualitySignal.RESPONSE_EMPTY in r.signals

    def test_response_truncated_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(response_text="Long...", response_truncated=True))
        assert QualitySignal.RESPONSE_TRUNCATED in r.signals

    def test_fallback_used_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(agent_fallback_used=True))
        assert QualitySignal.FALLBACK_USED in r.signals

    def test_consensus_used_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(consensus_used=True))
        assert QualitySignal.CONSENSUS_USED in r.signals

    def test_tool_used_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(tool_used=True))
        assert QualitySignal.TOOL_USED in r.signals

    def test_tool_failed_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(tool_failed=True))
        assert QualitySignal.TOOL_FAILED in r.signals

    def test_agent_failed_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(agent_failed=True))
        assert QualitySignal.AGENT_FAILED in r.signals

    def test_intent_unknown_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(intent="unknown"))
        assert QualitySignal.INTENT_UNKNOWN in r.signals

    def test_intent_low_confidence_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(intent_confidence=0.5))
        assert QualitySignal.INTENT_LOW_CONFIDENCE in r.signals

    def test_intent_confidence_at_boundary(self):
        from meta.reflection import QualitySignal, reflect

        # 0.6 is NOT low confidence (< 0.6 triggers it)
        r = reflect(_make_input(intent_confidence=0.6))
        assert QualitySignal.INTENT_LOW_CONFIDENCE not in r.signals

    def test_tier_upgraded_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(tier_was_upgraded=True))
        assert QualitySignal.TIER_UPGRADED in r.signals

    def test_degraded_mode_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(was_degraded_mode=True))
        assert QualitySignal.DEGRADED_MODE in r.signals

    def test_safety_blocked_signal(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(safety_blocked=True))
        assert QualitySignal.SAFETY_BLOCKED in r.signals


class TestReflectionReport:
    def test_report_fields_populated(self):
        from meta.reflection import reflect
        inp = _make_input(
            intent="code", lang="en", tier="HEAVY", model="gpt-oss-120b",
            response_text="x" * 100, llm_cost_usd=0.005,
            user_id=42, session_id="trace-abc",
        )
        r = reflect(inp)
        assert r.intent == "code"
        assert r.lang == "en"
        assert r.tier == "HEAVY"
        assert r.model == "gpt-oss-120b"
        assert r.response_len == 100
        assert r.llm_cost_usd == pytest.approx(0.005)
        assert r.user_id == 42
        assert r.session_id == "trace-abc"
        assert isinstance(r.timestamp_utc, str)
        assert r.lightweight is False

    def test_lightweight_mode_skips_notes(self):
        from meta.reflection import reflect
        r = reflect(_make_input(agent_fallback_used=True), lightweight=True)
        assert r.lightweight is True
        assert r.notes == []

    def test_full_mode_generates_notes(self):
        from meta.reflection import reflect
        r = reflect(_make_input(agent_fallback_used=True), lightweight=False)
        assert len(r.notes) > 0

    def test_has_signal_method(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(response_text=""))
        assert r.has_signal(QualitySignal.RESPONSE_EMPTY) is True
        assert r.has_signal(QualitySignal.CONSENSUS_USED) is False

    def test_to_dict_keys(self):
        from meta.reflection import reflect
        r = reflect(_make_input())
        d = r.to_dict()
        for key in ("timestamp_utc", "intent", "lang", "tier", "model",
                    "response_len", "llm_cost_usd", "signals", "notes",
                    "user_id", "session_id", "lightweight"):
            assert key in d

    def test_to_dict_signals_are_strings(self):
        from meta.reflection import QualitySignal, reflect
        r = reflect(_make_input(tool_used=True))
        d = r.to_dict()
        assert QualitySignal.TOOL_USED.value in d["signals"]

    def test_reflect_never_raises_on_bad_input(self):
        """reflect() must catch all exceptions and return a minimal report."""
        from meta.reflection import QualitySignal, reflect

        # Pass a broken object — reflect must not propagate
        r = reflect(object())  # type: ignore[arg-type]
        assert r.signals == [QualitySignal.RESPONSE_EMPTY]
        assert r.notes == ["ReflectionReport construction failed."]


# ══════════════════════════════════════════════════════════════════════════════
# llm/prompt_engine.py  (? % → ~90 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptEngine:
    def test_build_messages_minimal(self):
        from llm.prompt_engine import PromptContext, build_messages
        ctx = PromptContext(user_message="Hello")
        msgs = build_messages(ctx)
        # Should have system + user
        assert msgs[-1]["role"] == "user"
        assert "Hello" in msgs[-1]["content"]

    def test_build_messages_system_prompt_included(self):
        from llm.prompt_engine import PromptContext, build_messages
        ctx = PromptContext(user_message="q", system_prompt="You are Ceyona.")
        msgs = build_messages(ctx)
        system_msg = next(m for m in msgs if m["role"] == "system")
        assert "You are Ceyona." in system_msg["content"]

    def test_build_messages_strict_truth_block(self):
        from contracts.shared_types import TruthMode
        from llm.prompt_engine import _TRUTH_STRICT, PromptContext, build_messages
        ctx = PromptContext(user_message="q", truth_mode=TruthMode.STRICT)
        msgs = build_messages(ctx)
        system_msg = next(m for m in msgs if m["role"] == "system")
        assert _TRUTH_STRICT in system_msg["content"]

    def test_build_messages_hybrid_truth_block(self):
        # _TRUTH_HYBRID was deliberately removed per audit.md §session-4.
        # HYBRID intents receive retrieved context injected into the user turn as raw text.
        # Adding an explicit truth block caused meta-awareness loop (model narrated
        # about the context instead of using it). HYBRID → no truth block in system prompt.
        from contracts.shared_types import TruthMode
        from llm.prompt_engine import _TRUTH_STRICT, PromptContext, build_messages
        ctx = PromptContext(user_message="q", truth_mode=TruthMode.HYBRID)
        msgs = build_messages(ctx)
        system_msg = next(m for m in msgs if m["role"] == "system")
        assert _TRUTH_STRICT not in system_msg["content"]

    def test_build_messages_generative_no_truth_block(self):
        # _TRUTH_HYBRID removed per audit.md §session-4; only STRICT still exists.
        # GENERATIVE intents use no retrieval and no truth block at all.
        from contracts.shared_types import TruthMode
        from llm.prompt_engine import (
            _TRUTH_STRICT,
            PromptContext,
            build_messages,
        )
        ctx = PromptContext(user_message="q", truth_mode=TruthMode.GENERATIVE)
        msgs = build_messages(ctx)
        system_msg = next((m for m in msgs if m["role"] == "system"), None)
        if system_msg:
            assert _TRUTH_STRICT not in system_msg["content"]

    def test_build_messages_context_injected_into_user_turn(self):
        from llm.prompt_engine import PromptContext, build_messages
        ctx = PromptContext(user_message="What?", retrieved_context="Fact A.")
        msgs = build_messages(ctx)
        user_msg = msgs[-1]
        assert "Fact A." in user_msg["content"]
        assert "What?" in user_msg["content"]

    def test_build_messages_no_context_plain_user_turn(self):
        from llm.prompt_engine import PromptContext, build_messages
        ctx = PromptContext(user_message="Just ask")
        msgs = build_messages(ctx)
        assert msgs[-1]["content"] == "Just ask"

    def test_build_messages_conversation_history_injected(self):
        from llm.prompt_engine import PromptContext, build_messages

        # History content must share topic terms with user_message to pass
        # select_relevant_history's overlap filter (_MIN_HISTORY_OVERLAP=0.18).
        history = [
            {"role": "user", "content": "What is Python programming?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]
        ctx = PromptContext(user_message="Tell me about Python programming", conversation_history=history)
        msgs = build_messages(ctx)
        roles = [m["role"] for m in msgs]
        assert "user" in roles
        assert "assistant" in roles

    def test_build_messages_no_history(self):
        from llm.prompt_engine import PromptContext, build_messages
        ctx = PromptContext(user_message="Hi", conversation_history=None)
        msgs = build_messages(ctx)
        assert msgs[-1]["role"] == "user"

    def test_prompt_context_defaults(self):
        from contracts.shared_types import TruthMode
        from llm.prompt_engine import PromptContext
        ctx = PromptContext(user_message="x")
        assert ctx.system_prompt == ""
        assert ctx.retrieved_context == ""
        assert ctx.conversation_history is None
        assert ctx.truth_mode == TruthMode.HYBRID
        assert ctx.lang == "en"

    def test_build_system_prompt_persona_only(self):
        from llm.prompt_engine import build_system_prompt
        result = build_system_prompt(persona="You are helpful.")
        assert "You are helpful." in result

    def test_build_system_prompt_with_rules(self):
        from llm.prompt_engine import build_system_prompt
        result = build_system_prompt(rules=["Be concise", "No markdown"])
        assert "Be concise" in result
        assert "No markdown" in result

    def test_build_system_prompt_empty(self):
        from llm.prompt_engine import build_system_prompt
        assert build_system_prompt() == ""


# ══════════════════════════════════════════════════════════════════════════════
# agents/compound_agent.py  (? % → ~90 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestCompoundAgent:
    @pytest.mark.asyncio
    async def test_run_fast_success(self):
        from agents.compound_agent import run_fast
        mock_result = MagicMock()
        mock_result.text = "Search result"
        mock_result.model = "groq/compound-mini"
        mock_result.input_tokens = 100
        mock_result.output_tokens = 50
        with patch("agents.compound_agent.groq_client") as mock_client:
            mock_client.complete = AsyncMock(return_value=mock_result)
            result = await run_fast(messages=[{"role": "user", "content": "search"}])
        assert result.success is True
        assert result.text == "Search result"
        assert result.tool_calls == 0

    @pytest.mark.asyncio
    async def test_run_deep_success(self):
        from agents.compound_agent import run_deep
        mock_result = MagicMock()
        mock_result.text = "Deep result"
        mock_result.model = "groq/compound"
        mock_result.input_tokens = 200
        mock_result.output_tokens = 150
        with patch("agents.compound_agent.groq_client") as mock_client:
            mock_client.complete = AsyncMock(return_value=mock_result)
            result = await run_deep(messages=[{"role": "user", "content": "deep"}])
        assert result.success is True
        assert result.text == "Deep result"

    @pytest.mark.asyncio
    async def test_run_fast_api_failure_returns_failed_result(self):
        from agents.compound_agent import run_fast
        with patch("agents.compound_agent.groq_client") as mock_client:
            mock_client.complete = AsyncMock(side_effect=RuntimeError("API down"))
            result = await run_fast(messages=[{"role": "user", "content": "q"}])
        assert result.success is False
        assert result.text == ""
        assert "API down" in result.error

    @pytest.mark.asyncio
    async def test_run_deep_empty_text_is_not_success(self):
        from agents.compound_agent import run_deep
        mock_result = MagicMock()
        mock_result.text = "   "  # whitespace only
        mock_result.model = "groq/compound"
        mock_result.input_tokens = 50
        mock_result.output_tokens = 1
        with patch("agents.compound_agent.groq_client") as mock_client:
            mock_client.complete = AsyncMock(return_value=mock_result)
            result = await run_deep(messages=[])
        assert result.success is False

    @pytest.mark.asyncio
    async def test_run_fast_passes_lang_without_error(self):
        """lang param accepted for interface compat — must not break call."""
        from agents.compound_agent import run_fast
        mock_result = MagicMock()
        mock_result.text = "ok"
        mock_result.model = "groq/compound-mini"
        mock_result.input_tokens = 10
        mock_result.output_tokens = 5
        with patch("agents.compound_agent.groq_client") as mock_client:
            mock_client.complete = AsyncMock(return_value=mock_result)
            result = await run_fast(messages=[], lang="ru", temperature=0.3)
        assert result.success is True


# ══════════════════════════════════════════════════════════════════════════════
# notifications/event_notifier.py  (0 % → ~90 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestEventNotifier:
    @pytest.mark.asyncio
    async def test_on_balance_credited_no_email(self):
        from notifications.event_notifier import event_notifier
        with patch("notifications.event_notifier.email_service") as mock_email:
            await event_notifier.on_balance_credited(
                user_id=1, amount_usd=5.0, new_balance_usd=15.0,
                to_email=None,
            )
            mock_email.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_balance_credited_sends_email(self):
        from notifications.event_notifier import event_notifier
        with patch("notifications.event_notifier.email_service") as mock_email:
            mock_email.send = AsyncMock(return_value=True)
            await event_notifier.on_balance_credited(
                user_id=1, amount_usd=5.0, new_balance_usd=15.0,
                to_email="user@example.com", to_name="Alice",
            )
            mock_email.send.assert_awaited_once()
            call_kwargs = mock_email.send.call_args[1]
            assert call_kwargs["to_email"] == "user@example.com"
            assert "5.00" in call_kwargs["html_content"]

    @pytest.mark.asyncio
    async def test_on_balance_exhausted_no_email(self):
        from notifications.event_notifier import event_notifier
        with patch("notifications.event_notifier.email_service") as mock_email:
            await event_notifier.on_balance_exhausted(user_id=2)
            mock_email.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_balance_exhausted_sends_email(self):
        from notifications.event_notifier import event_notifier
        with patch("notifications.event_notifier.email_service") as mock_email:
            mock_email.send = AsyncMock(return_value=True)
            await event_notifier.on_balance_exhausted(
                user_id=2, to_email="u@e.com", to_name="Bob",
            )
            mock_email.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_safety_block(self):
        from notifications.event_notifier import event_notifier

        # Just must not raise
        await event_notifier.on_safety_block(user_id=3, reason="harmful_content")

    @pytest.mark.asyncio
    async def test_on_system_error(self):
        from notifications.event_notifier import event_notifier
        await event_notifier.on_system_error(error="Timeout", context={"tier": "HEAVY"})

    @pytest.mark.asyncio
    async def test_on_system_error_no_context(self):
        from notifications.event_notifier import event_notifier
        await event_notifier.on_system_error(error="Crash")

    def test_singleton_is_event_notifier_instance(self):
        from notifications.event_notifier import EventNotifier, event_notifier
        assert isinstance(event_notifier, EventNotifier)


# ══════════════════════════════════════════════════════════════════════════════
# payments/wallet_manager.py  (0 % → ~85 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestWalletManager:
    def _make_manager(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            manager = WalletManager(supabase)
        return manager

    def test_parse_user_id_valid(self):
        m = self._make_manager()
        assert m._parse_user_id("123456789") == 123456789

    def test_parse_user_id_with_spaces(self):
        m = self._make_manager()
        assert m._parse_user_id("  42  ") == 42

    def test_parse_user_id_invalid(self):
        m = self._make_manager()
        assert m._parse_user_id("not_a_number") is None

    def test_parse_user_id_empty(self):
        m = self._make_manager()
        assert m._parse_user_id("") is None

    def test_parse_user_id_none_like(self):
        m = self._make_manager()
        assert m._parse_user_id("None") is None

    @pytest.mark.asyncio
    async def test_is_processed_true_when_record_exists(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        result_mock = MagicMock()
        result_mock.data = {"tx_hash": "abc"}
        (supabase.table.return_value
             .select.return_value
             .eq.return_value
             .maybe_single.return_value
             .execute.return_value) = result_mock
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            m = WalletManager(supabase)
        assert await m._is_processed("abc") is True

    @pytest.mark.asyncio
    async def test_is_processed_false_when_no_record(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        result_mock = MagicMock()
        result_mock.data = None
        (supabase.table.return_value
             .select.return_value
             .eq.return_value
             .maybe_single.return_value
             .execute.return_value) = result_mock
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            m = WalletManager(supabase)
        assert await m._is_processed("xyz") is False

    @pytest.mark.asyncio
    async def test_is_processed_safe_default_on_exception(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        supabase.table.side_effect = Exception("db error")
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            m = WalletManager(supabase)
        # Safe default is True (treat as processed — no double credit)
        assert await m._is_processed("hash") is True

    @pytest.mark.asyncio
    async def test_mark_processed_calls_insert(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            m = WalletManager(supabase)
        await m._mark_processed("hash1", 99, 5.0)
        supabase.table.assert_called_with("processed_transactions")

    @pytest.mark.asyncio
    async def test_mark_processed_does_not_raise_on_exception(self):
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        supabase.table.side_effect = Exception("insert error")
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client"):
            m = WalletManager(supabase)
        await m._mark_processed("h", 1, 0.1)  # must not raise

    @pytest.mark.asyncio
    async def test_process_incoming_skips_duplicate(self):
        from payments.ton_client import TonTransaction
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        tx = TonTransaction(
            tx_hash="dup", from_address="addr", amount_nano=1_000_000_000,
            timestamp=0, comment="123",
        )
        result_mock = MagicMock()
        result_mock.data = {"tx_hash": "dup"}  # already processed
        (supabase.table.return_value
             .select.return_value
             .eq.return_value
             .maybe_single.return_value
             .execute.return_value) = result_mock
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client") as mock_ton:
            mock_ton.get_transactions = AsyncMock(return_value=[tx])
            m = WalletManager(supabase)
            count = await m.process_incoming()
        assert count == 0

    @pytest.mark.asyncio
    async def test_process_incoming_skips_unparseable_comment(self):
        from payments.ton_client import TonTransaction
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        tx = TonTransaction(
            tx_hash="bad_comment", from_address="addr", amount_nano=1_000_000_000,
            timestamp=0, comment="NOT_A_USER_ID",
        )
        result_mock = MagicMock()
        result_mock.data = None  # not processed yet
        (supabase.table.return_value
             .select.return_value
             .eq.return_value
             .maybe_single.return_value
             .execute.return_value) = result_mock
        supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        with patch("payments.wallet_manager.AccessController"), \
             patch("payments.wallet_manager.ton_client") as mock_ton, \
             patch("payments.wallet_manager.nano_to_usd", new_callable=AsyncMock):
            mock_ton.get_transactions = AsyncMock(return_value=[tx])
            m = WalletManager(supabase)
            count = await m.process_incoming()
        assert count == 0

    @pytest.mark.asyncio
    async def test_process_incoming_credits_valid_tx(self):
        from payments.ton_client import TonTransaction
        from payments.wallet_manager import WalletManager
        supabase = MagicMock()
        tx = TonTransaction(
            tx_hash="valid_tx", from_address="addr", amount_nano=2_000_000_000,
            timestamp=0, comment="777",
        )
        # Not processed yet
        not_processed = MagicMock()
        not_processed.data = None
        (supabase.table.return_value
             .select.return_value
             .eq.return_value
             .maybe_single.return_value
             .execute.return_value) = not_processed
        supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("payments.wallet_manager.ton_client") as mock_ton, \
             patch("payments.wallet_manager.nano_to_usd",
                   new_callable=AsyncMock, return_value=2.0), \
             patch("payments.wallet_manager.AccessController") as mock_ac_cls:
            mock_ton.get_transactions = AsyncMock(return_value=[tx])
            mock_ac = MagicMock()
            mock_ac.credit = AsyncMock(return_value=True)
            mock_ac_cls.return_value = mock_ac
            m = WalletManager(supabase)
            count = await m.process_incoming()

        assert count == 1


# ══════════════════════════════════════════════════════════════════════════════
# security/auth.py  (0 % → 100 %)
# security/origin_guard.py  (0 % → 100 %)
# ══════════════════════════════════════════════════════════════════════════════

def _mock_settings(**kwargs):
    """Return a MagicMock with sensible defaults for settings."""
    s = MagicMock()
    s.jwt_secret = kwargs.get("jwt_secret", "test_jwt_secret_32chars_padding!!")
    s.allowed_origins = kwargs.get("allowed_origins", "https://example.com,https://api.example.com")
    return s


class TestSecurityAuth:
    def test_create_and_verify_token(self):
        with patch("security.auth.settings", _mock_settings()):
            from security.auth import create_token, verify_token
            token = create_token(123)
            assert isinstance(token, str)
            assert len(token) > 0
            user_id = verify_token(token)
            assert user_id == 123

    def test_verify_token_invalid_returns_none(self):
        with patch("security.auth.settings", _mock_settings()):
            from security.auth import verify_token
            result = verify_token("not.a.valid.jwt.token")
            assert result is None

    def test_verify_token_wrong_secret_returns_none(self):
        s1 = _mock_settings(jwt_secret="secret_one_32chars_padding_here!")
        s2 = _mock_settings(jwt_secret="secret_two_32chars_padding_here!")
        with patch("security.auth.settings", s1):
            from security.auth import create_token
            token = create_token(42)
        with patch("security.auth.settings", s2):
            from security.auth import verify_token
            result = verify_token(token)
            assert result is None

    def test_verify_token_empty_string(self):
        with patch("security.auth.settings", _mock_settings()):
            from security.auth import verify_token
            assert verify_token("") is None


class TestSecurityOriginGuard:
    def test_wildcard_allows_any_origin(self):
        with patch("security.origin_guard.settings", _mock_settings(allowed_origins="*")):
            from security.origin_guard import is_allowed_origin
            assert is_allowed_origin("https://any.domain.com") is True
            assert is_allowed_origin("http://evil.site") is True

    def test_specific_origin_allowed(self):
        with patch("security.origin_guard.settings", _mock_settings(
            allowed_origins="https://example.com,https://api.example.com"
        )):
            from security.origin_guard import is_allowed_origin
            assert is_allowed_origin("https://example.com") is True
            assert is_allowed_origin("https://api.example.com") is True

    def test_unlisted_origin_denied(self):
        with patch("security.origin_guard.settings", _mock_settings(
            allowed_origins="https://example.com"
        )):
            from security.origin_guard import is_allowed_origin
            assert is_allowed_origin("https://evil.com") is False

    def test_empty_origins_denies_all(self):
        with patch("security.origin_guard.settings", _mock_settings(allowed_origins="")):
            from security.origin_guard import is_allowed_origin
            assert is_allowed_origin("https://example.com") is False

    def test_whitespace_trimmed_from_origins(self):
        with patch("security.origin_guard.settings", _mock_settings(
            allowed_origins=" https://example.com , https://api.example.com "
        )):
            from security.origin_guard import is_allowed_origin
            assert is_allowed_origin("https://example.com") is True


# ══════════════════════════════════════════════════════════════════════════════
# scripts/check_imports.py  (0 % → ~90 %)
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckImports:
    def test_layer_path_returns_path_object(self):
        from scripts.check_imports import layer_path
        p = layer_path("transport")
        assert isinstance(p, pathlib.Path)
        assert p.name == "transport"

    def test_layer_path_dot_notation(self):
        from scripts.check_imports import layer_path
        p = layer_path("core.kernel.cost_model")
        assert "core" in str(p)
        assert "kernel" in str(p)

    def test_get_imported_module_import_from(self):
        import ast as _ast

        from scripts.check_imports import get_imported_module
        node = _ast.parse("from cognition.intent_engine import Intent").body[0]
        assert get_imported_module(node) == "cognition.intent_engine"

    def test_get_imported_module_plain_import(self):
        import ast as _ast

        from scripts.check_imports import get_imported_module
        node = _ast.parse("import agents.fast_agent").body[0]
        assert get_imported_module(node) == "agents.fast_agent"

    def test_get_imported_module_empty_import_from(self):
        import ast as _ast

        from scripts.check_imports import get_imported_module

        # ImportFrom with no module (relative import `from . import x`)
        node = _ast.parse("from . import something").body[0]
        result = get_imported_module(node)
        assert result == "" or result is not None  # graceful, no crash

    def test_check_returns_list(self):
        from scripts.check_imports import check
        result = check()
        assert isinstance(result, list)

    def test_check_clean_codebase(self):
        """The actual project must pass its own architecture gate."""
        from scripts.check_imports import check
        errors = check()
        assert errors == [], "Architecture violations found:\n" + "\n".join(errors)

    def test_main_returns_0_on_clean(self):
        from scripts.check_imports import main

        # The project is clean, so main() must return 0
        result = main()
        assert result == 0

    def test_forbidden_list_not_empty(self):
        from scripts.check_imports import FORBIDDEN
        assert len(FORBIDDEN) > 0
        assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in FORBIDDEN)

    def test_check_detects_violation_in_temp_file(self, tmp_path):
        """Inject a synthetic violation and verify check() catches it."""
        # Find a valid forbidden pair whose source dir exists
        from scripts.check_imports import FORBIDDEN, ROOT, check
        pair = None
        for src, tgt in FORBIDDEN:
            src_dir = ROOT / src.replace(".", "/")
            if src_dir.exists():
                pair = (src, tgt)
                break

        if pair is None:
            pytest.skip("No testable forbidden pair found")

        source_layer, forbidden_target = pair
        src_dir = ROOT / source_layer.replace(".", "/")

        # Write a temp file inside the source layer with a forbidden import
        violating_file = src_dir / "_test_violation_temp.py"
        try:
            violating_file.write_text(f"import {forbidden_target}.something\n")
            errors = check()
            assert any("_test_violation_temp" in e for e in errors), \
                f"Expected violation not detected. Errors: {errors}"
        finally:
            if violating_file.exists():
                violating_file.unlink()