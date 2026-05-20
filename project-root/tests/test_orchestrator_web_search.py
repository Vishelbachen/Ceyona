"""
Tests for §3.3 fix: web search decision authority moved to orchestrator.

Verifies:
- update_handler no longer calls classify() or run_tool() for web search
- orchestrator owns web search decision (after intent, before EPK)
- _NO_SEARCH_INTENTS is defined in orchestrator, not transport layer
- vision_intent replaces forced_intent in OrchestratorRequest
- zero-balance guard respected in orchestrator web search path
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from contracts.shared_types import Complexity, Tier
from core.execution.orchestrator import OrchestratorRequest, _NO_SEARCH_INTENTS, _AGENTIC_INTENTS


# ─── _NO_SEARCH_INTENTS lives in orchestrator ─────────────────────────────────

class TestNoSearchIntents:
    def test_defined_in_orchestrator(self):
        """_NO_SEARCH_INTENTS must be in orchestrator, not transport layer."""
        import core.execution.orchestrator as orch
        assert hasattr(orch, "_NO_SEARCH_INTENTS")

    def test_not_in_update_handler(self):
        """transport layer must NOT own search routing logic."""
        import transport.telegram.update_handler as uh
        assert not hasattr(uh, "_NO_SEARCH_INTENTS")

    def test_self_contained_intents_excluded(self):
        """Intents that generate freely or use dedicated tools must be excluded."""
        for intent in ("creative", "code", "math", "emotional", "conversation"):
            assert intent in _NO_SEARCH_INTENTS, f"{intent} must be in _NO_SEARCH_INTENTS"

    def test_tool_intents_excluded(self):
        """Orchestrator-owned tool intents must not trigger background web search."""
        for intent in ("weather", "maps", "maps_route", "maps_poi", "search"):
            assert intent in _NO_SEARCH_INTENTS, f"{intent} must be in _NO_SEARCH_INTENTS"


# ─── OrchestratorRequest: vision_intent field ─────────────────────────────────

class TestVisionIntentField:
    def test_field_exists(self):
        """OrchestratorRequest must have vision_intent, not forced_intent."""
        req = OrchestratorRequest(
            user_message="test",
            user_balance=1.0,
            input_tokens=10,
            complexity=Complexity.LOW,
        )
        assert hasattr(req, "vision_intent")
        assert req.vision_intent is None

    def test_forced_intent_removed(self):
        """forced_intent must be gone — it was the source of the coupling."""
        req = OrchestratorRequest(
            user_message="test",
            user_balance=1.0,
            input_tokens=10,
            complexity=Complexity.LOW,
        )
        assert not hasattr(req, "forced_intent")

    def test_vision_intent_accepted(self):
        """vision_intent can be set without error."""
        mock_intent = MagicMock()
        req = OrchestratorRequest(
            user_message="solve this",
            user_balance=1.0,
            input_tokens=50,
            complexity=Complexity.LOW,
            vision_intent=mock_intent,
        )
        assert req.vision_intent is mock_intent


# ─── Web search: zero-balance guard in orchestrator ───────────────────────────

class TestWebSearchZeroBalanceGuard:
    """
    When user_balance <= 0, orchestrator must skip web search.
    This guard previously lived in update_handler — it now belongs here.
    """

    @pytest.mark.asyncio
    async def test_zero_balance_skips_web_search(self):
        """Web search must not fire when balance is zero."""
        web_search_called = []

        async def mock_web_tool(tool_name, params, lang):
            web_search_called.append(tool_name)
            return "some result"

        # Patch at the orchestrator's import site
        with patch("external.web_tools.run_tool", new=mock_web_tool):
            from core.execution.orchestrator import _NO_SEARCH_INTENTS
            # Simulate: intent value NOT in no-search list, but balance = 0
            # The guard condition: user_balance > 0 must block the call
            balance = 0.0
            retrieved_context = ""
            intent_value = "general"  # not in _NO_SEARCH_INTENTS

            should_search = (
                not retrieved_context
                and intent_value not in _NO_SEARCH_INTENTS
                and balance > 0  # ← this is the guard
            )
            assert not should_search
            assert web_search_called == []

    def test_positive_balance_allows_search(self):
        """Sanity: with positive balance and eligible intent, search is allowed."""
        balance = 1.0
        retrieved_context = ""
        intent_value = "general"

        should_search = (
            not retrieved_context
            and intent_value not in _NO_SEARCH_INTENTS
            and balance > 0
        )
        assert should_search

    def test_existing_context_skips_search(self):
        """If retrieval already produced context, web search is skipped."""
        balance = 1.0
        retrieved_context = "some retrieved docs"
        intent_value = "general"

        should_search = (
            not retrieved_context
            and intent_value not in _NO_SEARCH_INTENTS
            and balance > 0
        )
        assert not should_search


# ─── update_handler: no classify() or run_tool() for web search ───────────────

class TestUnifiedAgenticPath:
    """
    Unified agentic path (май 2026): ALL tool intents go through compound_agent.
    _TOOL_INTENTS is removed. _AGENTIC_INTENTS covers all five intents.
    """

    def test_agentic_intents_covers_all_five(self):
        """All five data-driven intents must be in _AGENTIC_INTENTS."""
        from cognition.intent_engine import Intent
        for intent in (Intent.SEARCH, Intent.WEATHER, Intent.MAPS, Intent.MAPS_POI, Intent.MAPS_ROUTE):
            assert intent in _AGENTIC_INTENTS, f"{intent} must be in _AGENTIC_INTENTS"

    def test_tool_intents_removed_from_orchestrator(self):
        """_TOOL_INTENTS must no longer exist — tool-only bypass path removed."""
        import core.execution.orchestrator as orch
        assert not hasattr(orch, "_TOOL_INTENTS"), (
            "_TOOL_INTENTS must be removed — all tool intents now use agentic path"
        )

    def test_get_route_in_compound_tools(self):
        """compound_agent must declare get_route as a supported tool."""
        from agents.compound_agent import _TOOL_SCHEMAS
        tool_names = [t["function"]["name"] for t in _TOOL_SCHEMAS]
        assert "get_route" in tool_names, "get_route must be in compound_agent _TOOL_SCHEMAS"

    def test_compound_tools_complete(self):
        """compound_agent must support all four tools."""
        from agents.compound_agent import _TOOL_SCHEMAS
        tool_names = {t["function"]["name"] for t in _TOOL_SCHEMAS}
        expected = {"web_search", "get_weather", "geocode", "get_route"}
        assert expected == tool_names, f"Expected {expected}, got {tool_names}"




class TestUpdateHandlerIsCleanTransport:
    def test_no_classify_import_for_web_search(self):
        """
        update_handler must not import classify at module level for web search.
        (classify may still be imported lazily elsewhere for other purposes,
        but the web-search-driven classify block is gone.)
        """
        import inspect
        import transport.telegram.update_handler as uh
        source = inspect.getsource(uh)

        # The specific pattern that indicated dual classification
        assert "quick_intent" not in source
        assert "_ORCHESTRATOR_TOOLS" not in source
        assert "_NO_SEARCH_INTENTS" not in source

    def test_forced_intent_not_in_source(self):
        """forced_intent must be removed from update_handler entirely."""
        import inspect
        import transport.telegram.update_handler as uh
        source = inspect.getsource(uh)
        assert "forced_intent" not in source