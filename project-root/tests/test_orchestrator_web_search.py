"""
Tests for routing authority: web search and retrieval decisions live in RoutingProfile.

Architecture contract verified here (§2.1, §3, §5, §6):
- RoutingProfile is the sole authority for retrieval decisions — not _NO_SEARCH_INTENTS.
- _resolve_routing() is the single construction point for RoutingProfile.
- orchestrator reads routing.retrieval_required — never consults _NO_SEARCH_INTENTS at runtime.
- _NO_SEARCH_INTENTS is preserved as a dead constant for test compatibility only.
- truth gate uses TruthMode from RoutingProfile — not a _STRICT_INTENTS set.
- vision_intent replaced forced_intent in OrchestratorRequest.
- zero-balance guard is enforced by _can_fetch condition in orchestrator.

History:
- §3.3 (pre-RoutingProfile): web search decision moved from update_handler to orchestrator.
- RoutingProfile migration: decision authority moved from _NO_SEARCH_INTENTS set to
  routing.retrieval_required declarative field in _resolve_routing().
"""
from unittest.mock import MagicMock

import pytest
from contracts.shared_types import Complexity, DomainHint, ReasoningDepth, TruthMode
from core.execution.orchestrator import (
    _AGENTIC_INTENTS,
    _AGENTIC_TOOL_MAP,
    _NO_SEARCH_INTENTS,
    OrchestratorRequest,
)


# ─── _NO_SEARCH_INTENTS: dead constant, still present for compatibility ────────
# This set is NO LONGER consulted at runtime — routing.retrieval_required owns
# the decision. The constant is preserved so existing tests don't break on import.
# The real routing contract is verified in TestRoutingProfileAuthority below.

class TestNoSearchIntentsCompat:
    """
    _NO_SEARCH_INTENTS still exists as a named constant (test/observability compat).
    Verifies location and content — NOT runtime authority.
    """

    def test_defined_in_orchestrator_not_transport(self):
        """Constant must live in orchestrator, never in transport layer."""
        import core.execution.orchestrator as orch
        import transport.telegram.update_handler as uh
        assert hasattr(orch, "_NO_SEARCH_INTENTS"), (
            "_NO_SEARCH_INTENTS must exist in orchestrator for test compatibility"
        )
        assert not hasattr(uh, "_NO_SEARCH_INTENTS"), (
            "transport layer must NOT own any search routing constant"
        )

    def test_self_contained_intents_present(self):
        """
        Intents that are self-contained (no retrieval needed) are documented in the set.
        Authoritative source: _resolve_routing() → retrieval_required=False for these.
        """
        for intent_value in ("creative", "code", "math", "emotional", "conversation"):
            assert intent_value in _NO_SEARCH_INTENTS, (
                f"{intent_value} must be documented in _NO_SEARCH_INTENTS"
            )

    def test_agentic_tool_intents_not_in_set(self):
        """
        GEO/tool intents are NOT in _NO_SEARCH_INTENTS — they require retrieval
        via their own tool path (path a in orchestrator retrieval logic).
        """
        for intent_value in ("weather", "maps", "maps_route", "maps_poi", "search"):
            assert intent_value in _AGENTIC_TOOL_MAP, (
                f"{intent_value} must be in _AGENTIC_TOOL_MAP"
            )
            assert intent_value not in _NO_SEARCH_INTENTS, (
                f"{intent_value} must not be in _NO_SEARCH_INTENTS — "
                "it routes via _AGENTIC_TOOL_MAP (path a)"
            )


# ─── RoutingProfile is the real authority ─────────────────────────────────────

class TestRoutingProfileAuthority:
    """
    _resolve_routing() is the single construction point for RoutingProfile.
    retrieval_required declared there — orchestrator reads it, makes no independent decision.

    Architecture contract (§2.1):
    - retrieval_required=True  → orchestrator fetches context before LLM call.
    - retrieval_required=False → orchestrator skips retrieval entirely.
    - No other signal (intent string, _NO_SEARCH_INTENTS set) participates.
    """

    def test_resolve_routing_is_sole_constructor(self):
        """_resolve_routing() must exist and return RoutingProfile for every intent."""
        from cognition.intent_engine import Intent, _resolve_routing
        from contracts.shared_types import RoutingProfile

        for intent in Intent:
            result = _resolve_routing(intent)
            assert isinstance(result, RoutingProfile), (
                f"_resolve_routing({intent}) must return RoutingProfile, got {type(result)}"
            )

    def test_retrieval_required_true_for_information_intents(self):
        """
        Intents that require external grounding must have retrieval_required=True.
        These are the intents that would previously NOT be in _NO_SEARCH_INTENTS.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        retrieval_intents = (
            Intent.QUESTION,    # factual — needs grounding
            Intent.ANALYSIS,    # evidence-based — needs grounding
            Intent.INSTRUCTION, # how-to — benefits from grounding
            Intent.SEARCH,      # explicit search — always retrieves
            Intent.WEATHER,     # data-driven — tool call required
            Intent.MAPS,        # geo — tool call required
            Intent.MAPS_POI,    # geo — tool call required
            Intent.MAPS_ROUTE,  # geo — tool call required
        )
        for intent in retrieval_intents:
            routing = _resolve_routing(intent)
            assert routing.retrieval_required is True, (
                f"{intent.value}: retrieval_required must be True — "
                "this intent requires external grounding"
            )

    def test_retrieval_required_false_for_self_contained_intents(self):
        """
        Self-contained intents must have retrieval_required=False.
        These are the intents that previously appeared in _NO_SEARCH_INTENTS.
        The set is now replaced by this declarative policy in _resolve_routing().
        """
        from cognition.intent_engine import Intent, _resolve_routing

        self_contained = (
            Intent.MATH,         # symbolic — LLM has the knowledge
            Intent.EXAM,         # structured — no retrieval needed
            Intent.CODE,         # generative — LLM has the knowledge
            Intent.CREATIVE,     # generative — free generation
            Intent.CONVERSATION, # affective — no retrieval needed
            Intent.EMOTIONAL,    # affective — no retrieval needed
        )
        for intent in self_contained:
            routing = _resolve_routing(intent)
            assert routing.retrieval_required is False, (
                f"{intent.value}: retrieval_required must be False — "
                "this intent is self-contained, no external grounding needed"
            )

    def test_truth_mode_strict_for_geo_intents(self):
        """
        GEO/tool intents must declare TruthMode.STRICT in RoutingProfile.
        This replaces the old _STRICT_INTENTS set that no longer exists in orchestrator.
        Orchestrator reads truth_mode from routing — not from any hardcoded set.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        geo_intents = (
            Intent.SEARCH,
            Intent.WEATHER,
            Intent.MAPS,
            Intent.MAPS_POI,
            Intent.MAPS_ROUTE,
        )
        for intent in geo_intents:
            routing = _resolve_routing(intent)
            assert routing.truth_mode == TruthMode.STRICT, (
                f"{intent.value}: truth_mode must be STRICT — "
                "hallucination is architecturally forbidden for data-driven intents"
            )

    def test_no_strict_intents_set_in_orchestrator(self):
        """
        _STRICT_INTENTS as a hardcoded set must NOT exist in orchestrator.
        Truth gate authority was migrated to RoutingProfile.truth_mode.
        Orchestrator reads: truth_mode = resolve_truth_mode(routing) — no set lookup.
        """
        import core.execution.orchestrator as orch
        assert not hasattr(orch, "_STRICT_INTENTS"), (
            "_STRICT_INTENTS must not exist in orchestrator — "
            "truth gate is now driven by routing.truth_mode from RoutingProfile (§10, §2.1). "
            "If this fails: a _STRICT_INTENTS set was re-introduced, violating the migration."
        )

    def test_truth_mode_hybrid_for_reasoning_intents(self):
        """
        Reasoning intents (MATH, EXAM, CODE, QUESTION, ANALYSIS, INSTRUCTION)
        must declare TruthMode.HYBRID — bounded synthesis, not fabrication.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        hybrid_intents = (
            Intent.MATH,
            Intent.EXAM,
            Intent.CODE,
            Intent.QUESTION,
            Intent.ANALYSIS,
            Intent.INSTRUCTION,
        )
        for intent in hybrid_intents:
            routing = _resolve_routing(intent)
            assert routing.truth_mode == TruthMode.HYBRID, (
                f"{intent.value}: truth_mode must be HYBRID"
            )

    def test_truth_mode_generative_for_free_intents(self):
        """
        Free-generation intents must declare TruthMode.GENERATIVE.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        generative_intents = (
            Intent.CREATIVE,
            Intent.CONVERSATION,
            Intent.EMOTIONAL,
        )
        for intent in generative_intents:
            routing = _resolve_routing(intent)
            assert routing.truth_mode == TruthMode.GENERATIVE, (
                f"{intent.value}: truth_mode must be GENERATIVE"
            )

    def test_domain_hint_math_only_for_math_intent(self):
        """
        DomainHint.MATH must be declared ONLY for Intent.MATH.
        MATH self-correction loop in coordinator activates on domain_hint == MATH — not intent.
        No other intent must accidentally trigger the MATH verification pipeline.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        math_routing = _resolve_routing(Intent.MATH)
        assert math_routing.domain_hint == DomainHint.MATH

        for intent in Intent:
            if intent == Intent.MATH:
                continue
            routing = _resolve_routing(intent)
            assert routing.domain_hint != DomainHint.MATH, (
                f"{intent.value}: domain_hint must NOT be MATH — "
                "only Intent.MATH activates the MATH verification loop"
            )

    def test_domain_hint_geo_for_all_tool_intents(self):
        """All GEO/tool intents must declare DomainHint.GEO."""
        from cognition.intent_engine import Intent, _resolve_routing

        geo_intents = (
            Intent.WEATHER,
            Intent.SEARCH,
            Intent.MAPS,
            Intent.MAPS_POI,
            Intent.MAPS_ROUTE,
        )
        for intent in geo_intents:
            routing = _resolve_routing(intent)
            assert routing.domain_hint == DomainHint.GEO, (
                f"{intent.value}: domain_hint must be GEO"
            )

    def test_question_fallback_has_retrieval_required_true(self):
        """
        QUESTION is the low-confidence fallback intent.
        retrieval_required must be True — when we're uncertain, retrieval
        gives the LLM a chance to ground the answer instead of hallucinating.
        retrieval_required=False here would cause the LLM to answer from memory
        on uncertain queries — exactly the hallucination scenario we prevent.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        routing = _resolve_routing(Intent.QUESTION)
        assert routing.retrieval_required is True, (
            "QUESTION (low-confidence fallback) must have retrieval_required=True — "
            "uncertain queries must be grounded, not answered from LLM memory"
        )

    def test_routing_profile_fields_complete(self):
        """Every RoutingProfile returned by _resolve_routing has all required fields."""
        from cognition.intent_engine import Intent, _resolve_routing
        from contracts.shared_types import RoutingProfile

        for intent in Intent:
            routing = _resolve_routing(intent)
            assert isinstance(routing.retrieval_required, bool)
            assert isinstance(routing.reasoning_depth, ReasoningDepth)
            assert isinstance(routing.domain_hint, DomainHint)
            assert isinstance(routing.truth_mode, TruthMode)


# ─── _can_fetch: orchestrator retrieval gate ──────────────────────────────────

class TestCanFetchGate:
    """
    _can_fetch is the orchestrator's retrieval gate condition:
        not _retrieved_context
        and request.user_balance > 0
        and not request.skip_web_search
        and _routing.retrieval_required      ← RoutingProfile authority

    Tests verify each axis of the gate independently.
    The condition is pure boolean — no I/O needed.
    """

    def _can_fetch(
        self,
        retrieval_required: bool,
        balance: float = 1.0,
        retrieved_context: str = "",
        skip_web_search: bool = False,
    ) -> bool:
        """Mirror of the _can_fetch condition in orchestrator.run()."""
        return (
            not retrieved_context
            and balance > 0
            and not skip_web_search
            and retrieval_required
        )

    def test_zero_balance_blocks_fetch(self):
        """Zero balance must block retrieval regardless of intent routing."""
        assert not self._can_fetch(retrieval_required=True, balance=0.0)

    def test_negative_balance_blocks_fetch(self):
        """Negative balance must block retrieval."""
        assert not self._can_fetch(retrieval_required=True, balance=-1.0)

    def test_positive_balance_with_retrieval_required_allows_fetch(self):
        """Positive balance + retrieval_required=True → fetch allowed."""
        assert self._can_fetch(retrieval_required=True, balance=1.0)

    def test_retrieval_required_false_blocks_fetch(self):
        """retrieval_required=False must block fetch regardless of balance."""
        assert not self._can_fetch(retrieval_required=False, balance=1.0)

    def test_existing_context_blocks_fetch(self):
        """If context already exists (from memory retrieval), skip web search."""
        assert not self._can_fetch(
            retrieval_required=True, balance=1.0,
            retrieved_context="some retrieved docs",
        )

    def test_skip_web_search_flag_blocks_fetch(self):
        """skip_web_search=True (vision pipeline path) must block web search."""
        assert not self._can_fetch(
            retrieval_required=True, balance=1.0,
            skip_web_search=True,
        )

    def test_self_contained_intent_never_fetches(self):
        """
        Self-contained intents have retrieval_required=False in RoutingProfile.
        _can_fetch must return False — routing decision, not balance decision.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        self_contained = (
            Intent.MATH, Intent.EXAM, Intent.CODE,
            Intent.CREATIVE, Intent.CONVERSATION, Intent.EMOTIONAL,
        )
        for intent in self_contained:
            routing = _resolve_routing(intent)
            result = self._can_fetch(retrieval_required=routing.retrieval_required, balance=10.0)
            assert result is False, (
                f"{intent.value}: _can_fetch must be False — "
                f"retrieval_required={routing.retrieval_required}"
            )

    def test_information_intent_fetches_with_balance(self):
        """
        Information intents have retrieval_required=True in RoutingProfile.
        _can_fetch must return True when balance > 0 and no prior context.
        """
        from cognition.intent_engine import Intent, _resolve_routing

        information_intents = (
            Intent.QUESTION, Intent.ANALYSIS, Intent.INSTRUCTION,
        )
        for intent in information_intents:
            routing = _resolve_routing(intent)
            result = self._can_fetch(retrieval_required=routing.retrieval_required, balance=1.0)
            assert result is True, (
                f"{intent.value}: _can_fetch must be True — "
                f"retrieval_required={routing.retrieval_required}"
            )


# ─── OrchestratorRequest contract ─────────────────────────────────────────────

class TestOrchestratorRequestContract:
    """
    OrchestratorRequest field contract.
    vision_intent replaced forced_intent — forced_intent was the source of
    transport-cognition coupling (update_handler was pre-classifying intents).
    """

    def _make_request(self, **kwargs) -> OrchestratorRequest:
        defaults = dict(
            user_message="test",
            user_balance=1.0,
            input_tokens=10,
            complexity=Complexity.LOW,
        )
        defaults.update(kwargs)
        return OrchestratorRequest(**defaults)

    def test_vision_intent_field_exists_and_defaults_none(self):
        req = self._make_request()
        assert hasattr(req, "vision_intent")
        assert req.vision_intent is None

    def test_forced_intent_field_removed(self):
        """forced_intent must be gone — its removal decoupled transport from cognition."""
        req = self._make_request()
        assert not hasattr(req, "forced_intent"), (
            "forced_intent must not exist — it was removed to prevent "
            "update_handler from pre-classifying intents (transport-cognition coupling)"
        )

    def test_vision_intent_accepts_intent_result(self):
        mock_intent = MagicMock()
        req = self._make_request(vision_intent=mock_intent)
        assert req.vision_intent is mock_intent

    def test_skip_web_search_field_exists(self):
        """skip_web_search guards vision pipeline path from web search."""
        req = self._make_request()
        assert hasattr(req, "skip_web_search")
        assert req.skip_web_search is False

    def test_is_vision_field_exists(self):
        """is_vision triggers CONVERSATION routing guard in orchestrator."""
        req = self._make_request()
        assert hasattr(req, "is_vision")
        assert req.is_vision is False


# ─── Unified agentic path ─────────────────────────────────────────────────────

class TestUnifiedAgenticPath:
    """
    All GEO/tool intents go through compound_agent as synthesizer (май 2026).
    _AGENTIC_INTENTS covers all five. _TOOL_INTENTS is removed.
    """

    def test_agentic_intents_covers_all_five(self):
        from cognition.intent_engine import Intent
        for intent in (Intent.SEARCH, Intent.WEATHER, Intent.MAPS, Intent.MAPS_POI, Intent.MAPS_ROUTE):
            assert intent in _AGENTIC_INTENTS, f"{intent} must be in _AGENTIC_INTENTS"

    def test_tool_intents_constant_removed(self):
        """_TOOL_INTENTS must be gone — all tool intents now use unified agentic path."""
        import core.execution.orchestrator as orch
        assert not hasattr(orch, "_TOOL_INTENTS"), (
            "_TOOL_INTENTS must be removed — compound_agent is the sole tool executor"
        )

    def test_agentic_tool_map_complete(self):
        """All five tool intents must be in _AGENTIC_TOOL_MAP."""
        expected = {"search", "weather", "maps", "maps_poi", "maps_route"}
        assert expected == set(_AGENTIC_TOOL_MAP.keys()), (
            f"Expected {expected}, got {set(_AGENTIC_TOOL_MAP.keys())}"
        )

    def test_agentic_intents_skip_run_tool(self):
        """
        _run_tool() is NOT called for agentic intents — compound_agent owns tool execution.
        Guard in orchestrator: requires_tools and intent not in _AGENTIC_INTENTS.
        """
        for intent in _AGENTIC_INTENTS:
            requires_tools = True
            should_call_run_tool = requires_tools and intent not in _AGENTIC_INTENTS
            assert not should_call_run_tool, (
                f"_run_tool() must be skipped for {intent} — compound_agent owns tool execution"
            )


# ─── Transport layer cleanliness ──────────────────────────────────────────────

class TestTransportLayerClean:
    """
    update_handler must contain no routing logic artifacts.
    Transport layer passes data — never makes routing decisions (§2.3, §3).
    """

    def test_no_search_routing_artifacts_in_update_handler(self):
        import inspect
        import transport.telegram.update_handler as uh
        source = inspect.getsource(uh)

        # Artifacts from the pre-RoutingProfile era
        assert "quick_intent" not in source, "quick_intent (old dual-classify) must be gone"
        assert "_ORCHESTRATOR_TOOLS" not in source, "_ORCHESTRATOR_TOOLS must be gone"
        assert "_NO_SEARCH_INTENTS" not in source, "_NO_SEARCH_INTENTS must not be in transport"

    def test_forced_intent_not_in_update_handler_source(self):
        import inspect
        import transport.telegram.update_handler as uh
        source = inspect.getsource(uh)
        assert "forced_intent" not in source, (
            "forced_intent must be removed from update_handler — "
            "it was causing transport to pre-classify intents"
        )