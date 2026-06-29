from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from cognition.intent_engine import (
    Intent,
    IntentResult,
    _resolve_routing,
    build_system_prompt,
    classify,
)
from cognition.multi_agent_coordinator import (
    CoordinationResult,
    coordinate,
    plan_agents,
)
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from context.assembler import resolve_truth_mode
from contracts.shared_types import (
    Complexity,
    EPKDecision,
    Tier,
    TruthMode,
)
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from events.event_bus import event_bus
from events.event_types import EPKDecisionEvent, EventName
from i18n.t import t
from llm.heavy_input_shaper import ShaperInput, shape
from llm.long_context_transformer import transform as _lc_transform
from llm.prompt_engine import PromptContext, build_messages
from observability.metrics import gauge, increment
from observability.tracing import trace
from retrieval.query_preprocessor import extract_query_profile

logger = logging.getLogger(__name__)

# ─── RETRIEVAL ROUTING ────────────────────────────────────────────────────────
# Authority over web search and tool retrieval now lives in RoutingProfile.
# routing.retrieval_required == False → skip both paths.
# routing.domain_hint == GEO + intent in _AGENTIC_TOOL_MAP → intent-specific tool.
# routing.retrieval_required == True + not GEO → generic web search.
#
# _AGENTIC_TOOL_MAP is kept here for the intent-specific tool call dispatch.
# It maps tool intents to their tool_name — internal to orchestrator.
# Owned here — not in transport layer.

_AGENTIC_TOOL_MAP: dict[str, str] = {
    "search":      "search",
    "weather":     "weather",
    "maps":        "maps",
    "maps_poi":    "maps_poi",
    "maps_route":  "maps_route",
}

# All tool intents that go through compound_agent as synthesizer.
_AGENTIC_INTENTS = {
    Intent.SEARCH,
    Intent.WEATHER,
    Intent.MAPS,
    Intent.MAPS_POI,
    Intent.MAPS_ROUTE,
}

# _NO_SEARCH_INTENTS is preserved as a named constant for test compatibility
# (test_orchestrator_web_search.py asserts it exists on orchestrator).
# It is NO LONGER consulted in the retrieval decision path — that decision
# is now made exclusively via routing.retrieval_required from RoutingProfile.
# The set is kept accurate for observability / documentation purposes.
_NO_SEARCH_INTENTS = {
    "creative", "conversation", "emotional", "code", "math",
}

# No-data fallback message key (goes to synthesizer)
_NO_GROUNDED_DATA = "no_grounded_data"
_SEARCH_NEED_MORE_CLUES = "search_need_more_clues"
_LIVE_DATA_UNAVAILABLE = "live_data_unavailable"


# ─── REQUEST / RESULT CONTRACTS ───────────────────────────────────────────────

@dataclass
class OrchestratorRequest:
    """
    Minimal contract from transport to orchestrator.

    Transport passes only what it knows from the Telegram update.
    All pipeline logic (Safety Gates, multilingual, analysis, history,
    retrieval) runs inside orchestrator.run().

    Architecture decision (Jun 2026):
      Transport: parse → auth → TTS → send.
      Orchestrator: everything else including history load/save.
    """
    user_message: str
    user_balance: float
    user_id: int = 0
    lang: str = "en"
    supabase: object = None
    redis: object = None
    hf_client: object = None
    input_type: str = "text"   # "text" | "image_group" | "voice" | "image"
    request_id: str = ""
    # Vision pipeline fields — set only on vision path (§15)
    vision_intent: object = None   # IntentResult | None
    is_vision: bool = False
    skip_web_search: bool = False
    vision_context: str = ""       # VQ-03: anchored image descriptions for grounding


@dataclass
class UsageRecord:
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    rerank_tokens: int
    tier: Tier
    embedding_type: str
    llm_cost_usd: float  # LLM + retrieval cost only — NOT total request cost.
                         # Safety Gate and multilingual costs are added in webhook.py:
                         # total_cost_usd = llm_cost_usd + safety_cost + _ml_cost
                         # On HEAVY path: also includes lc_transformer + shaper + safety_agent.
                         # Never read this field as "full cost" — use UsageEntry.raw_cost_usd.


@dataclass(frozen=True)
class PipelineMetrics:
    """
    Token metrics for pipeline stages that run outside coordinator:
    Safety Gates (Pass 1/2) and multilingual normalization.

    These are not coordinator-managed agents — they run before EPK,
    before coordinator is called. Kept separate from CoordinationMetrics
    so the boundary of coordinator authority stays explicit.

    Architecture decision (Jun 2026):
      CoordinationMetrics owns: primary, safety_agent, revision, lc_transformer.
      PipelineMetrics owns: safety_gate_pass1, safety_gate_pass2, multilingual.
      OrchestratorResult carries both — webhook/billing reads from both.
    """
    safety_pass1_tokens: int = 0              # llama-prompt-guard-2-22m input tokens
    safety_pass2_tokens: int = 0              # llama-prompt-guard-2-86m input tokens
    safety_safeguard_tokens: int = 0          # gpt-oss-safeguard-20b input (pass2)
    safety_safeguard_output_tokens: int = 0   # gpt-oss-safeguard-20b output (pass2)
    multilingual_input_tokens: int = 0        # multilingual_preprocessor LLM input
    multilingual_output_tokens: int = 0       # multilingual_preprocessor LLM output
    multilingual_model: str = ""              # "allam-2-7b" | "qwen/qwen3.6-27b" | "passthrough"


@dataclass
class OrchestratorResult:
    text: str
    tier: Tier
    model: str
    epk_decision: EPKDecision
    usage: UsageRecord
    denied: bool = False
    deny_reason: str = ""
    lang: str = "en"
    intent: str = ""          # classified intent value, for reflection/observability
    tool_used: bool = False   # whether an external tool was called
    tool_failed: bool = False # whether the tool call failed
    tts_audio_bytes: bytes = b""
    audio_seconds: float = 0.0
    tts_characters: int = 0
    tts_model: str = ""       # TTS model used: "canopylabs/orpheus-v1-english" | "canopylabs/orpheus-arabic-saudi"
                              # Required for billing: English=$22/1M chars, Arabic=$40/1M chars
    tool_calls: int = 0
    resolved_model: str = ""  # preferred_model resolved at routing time (models.md §25.3)

    # ── Structured metrics (Variant B — Jun 2026) ─────────────────────────────
    # agent_metrics: all coordinator-managed LLM agents (safety_agent, revision,
    #   primary, lc_transformer). Single source of truth inside coordinator.
    # pipeline_metrics: pipeline stages before coordinator (safety gates, multilingual).
    # webhook.py and usage_meter.py read from these — no flat token fields.
    agent_metrics: object = None   # CoordinationMetrics — imported lazily to avoid circular
    pipeline_metrics: object = None  # PipelineMetrics

    # Per-model token breakdown for compound AI systems (groq/compound, groq/compound-mini).
    # Populated from LLMResponse.usage_breakdown when compound_agent returns a result.
    # Used in webhook.py to call actual_compound_cost_from_breakdown() for exact billing.
    # Empty list when resolved_model is not a compound system or breakdown was absent.
    # BUG-02 fix. economic.md §1.3.
    compound_breakdown: list = None  # list[dict] — avoid mutable default in dataclass

    def __post_init__(self):
        if self.compound_breakdown is None:
            self.compound_breakdown = []
        if self.agent_metrics is None:
            from cognition.multi_agent_coordinator import CoordinationMetrics
            self.agent_metrics = CoordinationMetrics()
        if self.pipeline_metrics is None:
            self.pipeline_metrics = PipelineMetrics()

    # ── Convenience accessors (read-only facade over structured metrics) ───────
    # These properties let webhook/usage_meter access tokens without knowing
    # whether they came from coordinator or pipeline stage. Zero boilerplate.

    @property
    def safety_pass1_tokens(self) -> int:
        return self.pipeline_metrics.safety_pass1_tokens

    @property
    def safety_pass2_tokens(self) -> int:
        return self.pipeline_metrics.safety_pass2_tokens

    @property
    def safety_safeguard_tokens(self) -> int:
        return self.pipeline_metrics.safety_safeguard_tokens

    @property
    def safety_safeguard_output_tokens(self) -> int:
        return self.pipeline_metrics.safety_safeguard_output_tokens

    @property
    def safety_agent_input_tokens(self) -> int:
        return self.agent_metrics.safety.input_tokens

    @property
    def safety_agent_output_tokens(self) -> int:
        return self.agent_metrics.safety.output_tokens

    @property
    def revision_input_tokens(self) -> int:
        return self.agent_metrics.revision.input_tokens

    @property
    def revision_output_tokens(self) -> int:
        return self.agent_metrics.revision.output_tokens

    @property
    def multilingual_input_tokens(self) -> int:
        return self.pipeline_metrics.multilingual_input_tokens

    @property
    def multilingual_output_tokens(self) -> int:
        return self.pipeline_metrics.multilingual_output_tokens

    @property
    def multilingual_model(self) -> str:
        return self.pipeline_metrics.multilingual_model

    @property
    def lc_transformer_input_tokens(self) -> int:
        return self.agent_metrics.lc_transformer.input_tokens

    @property
    def lc_transformer_output_tokens(self) -> int:
        return self.agent_metrics.lc_transformer.output_tokens


# ─── INTERNAL HELPERS ─────────────────────────────────────────────────────────

def _denied_result(
    reason: str,
    lang: str,
    tier: Tier = Tier.FAST,
    input_tokens: int = 0,
    embedding_tokens: int = 0,
    rerank_tokens: int = 0,
    embedding_type: str = "large",
    epk_decision: EPKDecision = EPKDecision.DENY,
) -> OrchestratorResult:
    synthesis = synthesize(SynthesisInput(
        raw_text="",
        intent=None,
        tier=tier,
        denied=True,
        deny_reason=reason,
        lang=lang,
    ))
    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model="",
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=input_tokens,
            output_tokens=0,
            embedding_tokens=embedding_tokens,
            rerank_tokens=rerank_tokens,
            tier=tier,
            embedding_type=embedding_type,
            llm_cost_usd=0.0,
        ),
        denied=True,
        deny_reason=reason,
        lang=lang,
    )


def _empty_usage(
    request: OrchestratorRequest,
    tier: Tier = Tier.FAST,
) -> UsageRecord:
    return UsageRecord(
        input_tokens=request.input_tokens,
        output_tokens=0,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
        llm_cost_usd=0.0,
    )


def _clarify_result(
    key: str,
    lang: str,
    request: OrchestratorRequest,
    tier: Tier = Tier.FAST,
    embedding_type: str = "large",
    epk_decision: EPKDecision = EPKDecision.DENY,
) -> OrchestratorResult:
    synthesis = synthesize(SynthesisInput(
        raw_text=t(key, lang),
        intent=None,
        tier=tier,
        denied=False,
        lang=lang,
    ))
    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model="rule-based-clarification",
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=request.input_tokens,
            output_tokens=0,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=tier,
            embedding_type=embedding_type,
            llm_cost_usd=0.0,
        ),
        denied=False,
        deny_reason="",
        lang=lang,
    )


# ─── TOOL RUNNER ──────────────────────────────────────────────────────────────

async def _run_tool(intent_result: IntentResult, lang: str) -> str | None:
    if not intent_result.requires_tools or not intent_result.tool_name:
        return None
    try:
        from external.web_tools import run_tool
        result = await run_tool(
            tool_name=intent_result.tool_name,
            params=intent_result.tool_params,
            lang=lang,
        )
        logger.info("Tool executed", extra={
            "tool": intent_result.tool_name,
            "result_len": len(result) if result else 0,
        })
        return result
    except Exception as exc:
        logger.error("Tool execution failed", extra={
            "tool": intent_result.tool_name,
            "error": str(exc),
        }, exc_info=True)
        return None


def _has_specific_airport_reference(text: str) -> bool:
    """Return True when the user already named a concrete airport origin."""
    if re.search(r"\b[A-Z]{3}\b", text):
        return True

    airport_patterns = [
        r"\b[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*)*\s+(?:airport|аэропорт|aeroporto|aéroport|flugha?fen|aeropuerto)\b",
        r"\b(?:airport|аэропорт|aeroporto|aéroport|flugha?fen|aeropuerto)\s+[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*)*\b",
    ]
    return any(re.search(pattern, text) for pattern in airport_patterns)


def _needs_clarification(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    profile,
    retrieved_context: str,
    tool_output: str | None,
) -> str:
    """Return an i18n key when the request needs a single clarifying detail."""
    if intent_result.intent == Intent.RECALL:
        if not retrieved_context and not tool_output:
            return "need_more_clues"
        return ""

    if intent_result.intent == Intent.RECOMMENDATION:
        text = profile.normalized_text
        lower = text.casefold()
        if profile.route_requested:
            if _has_specific_airport_reference(text):
                return ""
            if re.search(r"\b(airport|аэропорт|aeroporto|aéroport|flugha?fen|aeropuerto)\b", lower):
                return "need_route_origin"
            if re.search(r"\b(from|из|de|desde|von)\b.*\b(to|до|a|vers|nach)\b", lower):
                return "need_route_origin"
        if (profile.hotel_requested or profile.travel_requested) and not profile.location:
            return "need_city_or_area"

    return ""


async def _fetch_external_grounding(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    lang: str,
) -> str:
    """
    Resolve external grounding context for the current request.

    Agentic intents go through the same dispatcher as non-agentic tools, but
    use normalized tool parameters coming from intent classification.
    """
    if request.retrieved_context:
        return request.retrieved_context

    if request.user_balance <= 0 or request.skip_web_search or not intent_result.routing.retrieval_required:
        return ""

    _intent_value = intent_result.intent.value

    if _intent_value in _AGENTIC_TOOL_MAP:
        _tool_name = _AGENTIC_TOOL_MAP[_intent_value]
        try:
            from external.web_tools import run_tool as _web_run_tool
            tool_result = await _web_run_tool(
                tool_name=_tool_name,
                params=intent_result.tool_params or {"query": request.user_message, "lang": lang},
                lang=lang,
            )
            if tool_result:
                logger.info("Agentic retrieval: context acquired", extra={
                    "intent": _intent_value,
                    "tool": _tool_name,
                    "chars": len(tool_result),
                })
                return tool_result
            logger.warning("Agentic retrieval: empty result", extra={
                "intent": _intent_value,
                "tool": _tool_name,
            })
        except Exception as exc:
            logger.warning("Agentic retrieval failed — continuing without", extra={
                "intent": _intent_value,
                "tool": _tool_name,
                "error": str(exc),
            })
        return ""

    try:
        from external.web_tools import run_tool as _web_run_tool
        web_result = await _web_run_tool(
            tool_name="search",
            params={"query": request.user_message, "lang": lang},
            lang=lang,
        )
        if web_result:
            logger.info("Web search: context acquired", extra={
                "intent": _intent_value,
                "chars": len(web_result),
            })
            return web_result
    except Exception as exc:
        logger.warning("Web search failed — continuing without", extra={"error": str(exc)})

    return ""


# ─── PROMPT BUILDER (truth-aware) ────────────────────────────────────────────

def _build_messages(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    retrieved_context: str,
    truth_mode: TruthMode,
    tier: Tier = Tier.GENERAL,
) -> list[dict]:
    # Use real tier so FAST requests get lightweight instruction_prefix.
    strategy = select_strategy(intent_result.routing, tier)
    user_msg = (
        f"{strategy.instruction_prefix} {request.user_message}".strip()
        if strategy.instruction_prefix
        else request.user_message
    )
    return build_messages(PromptContext(
        user_message=user_msg,
        system_prompt=request.system_prompt or intent_result.system_prompt,
        retrieved_context=retrieved_context,
        conversation_history=request.conversation_history,
        truth_mode=truth_mode,
        lang=request.lang,
        tier=tier.value.lower(),
    ))


# ─── EXECUTION PATHS ──────────────────────────────────────────────────────────

async def _run_allow(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    messages: list[dict],
    tier: Tier,
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    strategy = select_strategy(intent_result.routing, tier)
    plan = plan_agents(intent_result.routing, tier, strategy, intent=intent_result.intent)

    increment(f"orchestrator.tier.{tier.value.lower()}")
    with trace("coordinator", tier=tier.value, intent=str(intent_result.intent)):
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
            routing=intent_result.routing,
            temperature=strategy.temperature,
            intent=intent_result.intent,
            lang=lang,
            tier=tier,
        )

    if coordination.blocked:
        if intent_result.intent == Intent.RECALL:
            return _clarify_result(
                "need_more_clues",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        if intent_result.intent == Intent.RECOMMENDATION:
            return _clarify_result(
                "no_grounded_data",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        return _denied_result(
            reason=coordination.block_reason or "default_deny",
            lang=lang,
            tier=tier,
            input_tokens=request.input_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            embedding_type=request.embedding_type,
            epk_decision=epk_decision,
        )

    _billing_tier = coordination.actual_tier or tier
    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=_billing_tier,
        embedding_type=request.embedding_type,
    )

    # BUG-O1 fix: safety_agent runs on consensus paths (CREATIVE, CODE, MATH, ANALYSIS,
    # SEARCH/RECOMMENDATION — all have use_consensus=True in plan_agents()).
    # Tokens arrive in CoordinationResult but were never billed or propagated.
    # economic.md §2: every model call MUST be billed.
    # Model: gpt-oss-safeguard-20b ($0.075 input / $0.30 output per 1M).
    from core.kernel.cost_model import actual_safety_cost as _actual_safety_cost
    _sa_cost = _actual_safety_cost(
        pass1_tokens=0,
        pass2_tokens=0,
        safeguard_tokens=coordination.coordination_metrics.safety.input_tokens,
        safeguard_output_tokens=coordination.coordination_metrics.safety.output_tokens,
    )
    cost += _sa_cost

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
        from_vision=request.vision_intent is not None,
        conversation_history=request.conversation_history,
    ))

    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model=coordination.model,
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=_billing_tier,
            embedding_type=request.embedding_type,
            llm_cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model=intent_result.routing.preferred_model or "",
        agent_metrics=coordination.coordination_metrics,
        compound_breakdown=getattr(coordination, "usage_breakdown", []),
    )


async def _run_degraded(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    messages: list[dict],
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    tier = Tier.FAST
    strategy = select_strategy(intent_result.routing, tier)
    plan = plan_agents(intent_result.routing, tier, strategy, intent=intent_result.intent)

    increment(f"orchestrator.tier.{tier.value.lower()}")
    with trace("coordinator", tier=tier.value, intent=str(intent_result.intent)):
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
            routing=intent_result.routing,
            temperature=strategy.temperature,
            intent=intent_result.intent,
            lang=lang,
            tier=tier,
        )

    if coordination.blocked:
        if intent_result.intent == Intent.RECALL:
            return _clarify_result(
                "need_more_clues",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        if intent_result.intent == Intent.RECOMMENDATION:
            return _clarify_result(
                "no_grounded_data",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        return _denied_result(
            reason=coordination.block_reason or "default_deny",
            lang=lang,
            tier=tier,
            input_tokens=request.input_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            embedding_type=request.embedding_type,
            epk_decision=epk_decision,
        )

    # ── Safety Lite (architecture.md §21, SAFETY-4) ───────────────────────────
    # FAST/DEGRADED path: BLOCK-scope only. No reasoning chain on FAST — REVISE
    # semantics (medical/legal disclaimers) do not apply. Same model, lighter prompt.
    from agents.safety_agent import SafetyInput, SafetyVerdict
    from agents.safety_agent import check_async_lite as _safety_lite

    _lite_result = await _safety_lite(SafetyInput(
        reasoning_plan="",  # no reasoning chain on FAST/DEGRADED path
        draft_response=coordination.text,
        user_message=request.user_message,
    ))

    if _lite_result.verdict == SafetyVerdict.BLOCK:
        logger.warning("safety_agent Lite BLOCK on DEGRADED path",
                       extra={"reason": _lite_result.reason})
        return _denied_result(
            reason="safety_block",
            lang=lang,
            tier=tier,
            input_tokens=request.input_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            embedding_type=request.embedding_type,
            epk_decision=epk_decision,
        )
    if _lite_result.verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
        logger.warning("safety_agent Lite UNAVAILABLE on DEGRADED — proceeding fail-open")

    _billing_tier = coordination.actual_tier or tier
    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=_billing_tier,
        embedding_type=request.embedding_type,
    )

    # Bill Safety Lite tokens (economic.md §2: every model call MUST be billed).
    from core.kernel.cost_model import actual_safety_cost as _actual_safety_cost
    _lite_cost = _actual_safety_cost(
        pass1_tokens=0,
        pass2_tokens=0,
        safeguard_tokens=_lite_result.input_tokens,
        safeguard_output_tokens=_lite_result.output_tokens,
    )
    cost += _lite_cost

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
        from_vision=request.vision_intent is not None,
        conversation_history=request.conversation_history,
    ))

    from cognition.multi_agent_coordinator import AgentCallMetrics as _ACM
    _degraded_metrics = coordination.coordination_metrics.with_agent(
        "safety",
        _ACM(
            model="openai/gpt-oss-safeguard-20b",
            input_tokens=_lite_result.input_tokens,
            output_tokens=_lite_result.output_tokens,
        ),
    )

    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model=coordination.model,
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=_billing_tier,
            embedding_type=request.embedding_type,
            llm_cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model="",  # DEGRADED_MODE: no preferred_model — FAST tier is always gpt-oss-20b
        agent_metrics=_degraded_metrics,
        compound_breakdown=getattr(coordination, "usage_breakdown", []),
    )


async def _run_heavy(
    request: OrchestratorRequest,
    intent_result: IntentResult,
    messages: list[dict],
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    tier = Tier.HEAVY
    strategy = select_strategy(intent_result.routing, tier)

    # Track whether Role B compression succeeded — shaper must use compressed text if so.
    _lc_compressed_text: str | None = None

    # ── Long-Context Role B (models.md §26.2) ────────────────────────────────
    # Activation: complexity == CRITICAL AND context_length > 32K tokens.
    # qwen/qwen3.6-27b (262K native ctx) compresses input for gpt-oss-120b.
    # This is a pre-synthesis transformation step — NOT a reasoning step.
    # reasoning_effort="none" is mandatory. Must not substitute for gpt-oss-120b
    # on reasoning tasks — it only reduces input size before Heavy Tier execution.
    _LC_TOKEN_THRESHOLD = 32_000
    if (
        request.complexity == Complexity.CRITICAL
        and request.input_tokens > _LC_TOKEN_THRESHOLD
    ):
        try:
            lc_result = await _lc_transform(
                user_message=request.user_message,
                retrieved_context=request.retrieved_context or "",
                conversation_history=request.conversation_history,
                input_tokens=request.input_tokens,
            )
            if lc_result.success and lc_result.compressed_text:
                logger.info(
                    "Long-Context Role B: input compressed",
                    extra={
                        "original_tokens": request.input_tokens,
                        "compressed_chars": len(lc_result.compressed_text),
                        "model": lc_result.model_used,
                    },
                )
                _lc_compressed_text = lc_result.compressed_text
                # Rebuild messages with compressed input — same truth_mode, same tier
                truth_mode = resolve_truth_mode(intent_result.routing)
                messages = build_messages(PromptContext(
                    user_message=lc_result.compressed_text,
                    system_prompt=request.system_prompt or intent_result.system_prompt,
                    retrieved_context="",  # already folded into compressed_text by transformer
                    conversation_history=request.conversation_history,
                    truth_mode=truth_mode,
                    lang=request.lang,
                    tier=tier.value.lower(),
                ))
        except Exception as exc:
            # Role B failure is non-fatal — continue with original messages.
            # Heavy Tier handles long context natively (gpt-oss-120b: 40+ sentence capacity).
            logger.warning(
                "Long-Context Role B failed — continuing with original input",
                extra={"error": str(exc)},
            )

    # Shaper receives the compressed text if Role B succeeded, otherwise the original.
    # This prevents shaper from rebuilding messages from the original long input and
    # silently discarding the Role B compression output.
    _shaper_input_text = _lc_compressed_text if _lc_compressed_text else request.user_message
    shaper_result = await shape(ShaperInput(
        text=_shaper_input_text,
        token_count=request.input_tokens,
        has_code_block=request.has_code_block,
        has_json_shape=request.has_json_shape,
        context_size=request.context_size,
    ))

    if shaper_result.was_shaped:
        logger.info("heavy_input_shaper shaped input", extra={
            "operation": shaper_result.operation,
        })
        truth_mode = resolve_truth_mode(intent_result.routing)
        messages = build_messages(PromptContext(
            user_message=shaper_result.text,
            system_prompt=request.system_prompt or intent_result.system_prompt,
            # If Role B already folded retrieved_context into compressed_text, don't append it again.
            retrieved_context="" if _lc_compressed_text else (request.retrieved_context or ""),
            conversation_history=request.conversation_history,
            truth_mode=truth_mode,
            lang=request.lang,
            tier=tier.value.lower(),
        ))

    plan = plan_agents(intent_result.routing, tier, strategy, intent=intent_result.intent)

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        routing=intent_result.routing,
        reasoning_plan="",
        temperature=strategy.temperature,
        intent=intent_result.intent,
        lang=lang,
        tier=tier,
    )

    if coordination.blocked:
        if intent_result.intent == Intent.RECALL:
            return _clarify_result(
                "need_more_clues",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        if intent_result.intent == Intent.RECOMMENDATION:
            return _clarify_result(
                "no_grounded_data",
                lang=lang,
                request=request,
                tier=tier,
                embedding_type=request.embedding_type,
                epk_decision=epk_decision,
            )
        return _denied_result(
            reason=coordination.block_reason or "default_deny",
            lang=lang,
            tier=tier,
            input_tokens=request.input_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            embedding_type=request.embedding_type,
            epk_decision=epk_decision,
        )

    _billing_tier = coordination.actual_tier or tier

    # long_context_transformer billing — uses qwen3.6-27b ($0.60/$3.00 per 1M).
    # economic.md §2: every model call MUST be billed. Tokens from LongContextResult.
    # BUG-O4 fix: dir() does not reliably check local variables — use locals() instead.
    _lc_in_tok  = lc_result.input_tokens  if "lc_result" in locals() and lc_result.success else 0
    _lc_out_tok = lc_result.output_tokens if "lc_result" in locals() and lc_result.success else 0
    _lc_cost = actual_cost(
        input_tokens=_lc_in_tok,
        output_tokens=_lc_out_tok,
        embedding_tokens=0,
        rerank_tokens=0,
        tier=Tier.GENERAL,  # qwen3.6-27b is GENERAL tier
        embedding_type=request.embedding_type,
    ) if _lc_in_tok else 0.0

    # heavy_input_shaper billing — uses gpt-oss-20b (FAST tier, $0.075/$0.30 per 1M).
    # models.md §5: SHAPER_MODEL = openai/gpt-oss-20b — NOT qwen3.6-27b.
    # economic.md §2: every model call MUST be billed. Tokens from ShaperResult.
    # BUG-O2 fix: was Tier.GENERAL ($0.60/$3.00) — wrong model, ~8x output overcharge.
    _shaper_cost = actual_cost(
        input_tokens=shaper_result.shaper_input_tokens,
        output_tokens=shaper_result.shaper_output_tokens,
        embedding_tokens=0,
        rerank_tokens=0,
        tier=Tier.FAST,  # gpt-oss-20b = FAST tier
        embedding_type=request.embedding_type,
    ) if shaper_result.was_shaped else 0.0

    # safety_agent billing — LLM judge uses gpt-oss-safeguard-20b ($0.075/$0.30 per 1M).
    # Separate from Safety Gate (different call site, different purpose).
    # Tokens flow from CoordinationResult.safety_agent_input/output_tokens.
    from core.kernel.cost_model import actual_safety_cost as _actual_safety_cost
    _safety_agent_cost = _actual_safety_cost(
        pass1_tokens=0,
        pass2_tokens=0,
        safeguard_tokens=coordination.coordination_metrics.safety.input_tokens,
        safeguard_output_tokens=coordination.coordination_metrics.safety.output_tokens,
    )

    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=_billing_tier,
        embedding_type=request.embedding_type,
    ) + _lc_cost + _shaper_cost + _safety_agent_cost

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
        from_vision=request.vision_intent is not None,
        conversation_history=request.conversation_history,
    ))

    from cognition.multi_agent_coordinator import AgentCallMetrics as _ACM
    _heavy_metrics = coordination.coordination_metrics
    if _lc_in_tok:
        _heavy_metrics = _heavy_metrics.with_agent(
            "lc_transformer",
            _ACM(
                model="qwen/qwen3.6-27b",
                input_tokens=_lc_in_tok,
                output_tokens=_lc_out_tok,
            ),
        )

    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model=coordination.model,
        epk_decision=epk_decision,
        usage=UsageRecord(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=_billing_tier,
            embedding_type=request.embedding_type,
            llm_cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model=intent_result.routing.preferred_model or "",
        agent_metrics=_heavy_metrics,
        compound_breakdown=getattr(coordination, "usage_breakdown", []),
    )


# ─── PIPELINE DATA CONTRACTS ─────────────────────────────────────────────────
# Internal data contract used between pipeline stages inside orchestrator.
# Not visible to the transport layer.
# Transport-facing OrchestratorRequest is minimal; _InternalRequest is rich.

@dataclass
class _InternalRequest:
    """Internal request populated after Safety Gates, multilingual, history, retrieval."""
    user_message: str
    user_balance: float
    input_tokens: int
    complexity: Complexity
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    embedding_tokens: int = 0
    rerank_tokens: int = 0
    embedding_type: str = "large"
    lang: str = "en"
    has_code_block: bool = False
    has_json_shape: bool = False
    context_size: int = 0
    vision_intent: object = None
    supabase: object = None
    hf_client: object = None
    input_type: str = "text"
    request_id: str = ""
    analysis_report: object = None
    skip_web_search: bool = False
    is_vision: bool = False
    vision_context: str = ""    # VQ-03: anchored image descriptions — passed from OrchestratorRequest


async def _run_pipeline(request: _InternalRequest) -> OrchestratorResult:
    lang = request.lang or "en"

    _rid = request.request_id or ""
    logger.info("Orchestrator start", extra={
        "request_id":  _rid,
        "message_len": len(request.user_message),
        "input_tokens": request.input_tokens,
        "complexity": request.complexity,
        "lang": lang,
        "balance": request.user_balance,
    })

    try:
        # ── intent ───────────────────────────────────────────────────────────
        # Use pre-computed intent from vision_handler (§15) when available.
        if request.vision_intent is not None and request.vision_intent.confidence >= 0.6:
            intent_result = request.vision_intent
            logger.info("Intent (vision)", extra={
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
            })
        else:
            intent_result = await classify(
                request.user_message,
                lang=lang,
                supabase=request.supabase,
                hf_client=request.hf_client,
                conversation_history=request.conversation_history,
                analysis_hints=request.analysis_report,
            )
            logger.info("Intent", extra={
                "intent":           intent_result.intent,
                "confidence":       intent_result.confidence,
                "routing.depth":    intent_result.routing.reasoning_depth,
                "routing.domain":   intent_result.routing.domain_hint,
                "routing.retrieval":intent_result.routing.retrieval_required,
                "routing.truth":    intent_result.routing.truth_mode,
            })

        # ── is_vision routing guard ──────────────────────────────────────────
        # Vision descriptions are LLM-generated text, NOT user intent.
        # Force CONVERSATION + LOW complexity to prevent CoT artefacts (§15).
        if request.is_vision:
            _conv_routing = _resolve_routing(Intent.CONVERSATION)
            intent_result = IntentResult(
                intent=Intent.CONVERSATION,
                confidence=1.0,
                system_prompt=build_system_prompt(Intent.CONVERSATION, lang),
                requires_retrieval=_conv_routing.retrieval_required,
                requires_tools=False,
                routing=_conv_routing,
            )
            request = type(request)(**{
                **request.__dict__,
                "complexity": Complexity.LOW,
            })
            logger.info("Vision routing guard applied — forced CONVERSATION + LOW complexity", extra={
                "request_id": _rid,
            })

        # ── retrieval ────────────────────────────────────────────────────────
        # Decision authority: routing.retrieval_required from RoutingProfile.
        # routing.retrieval_required == False → skip both retrieval paths.
        # routing.domain_hint == GEO → intent-specific tool call (path a).
        # routing.retrieval_required == True + not GEO → generic web search (path b).
        #
        # Zero-balance guard and skip_web_search flag apply before both paths.
        _routing = intent_result.routing
        _retrieved_context = await _fetch_external_grounding(request, intent_result, lang)

        # ── truth mode — from RoutingProfile ──────────────────────────────────
        # Single source of truth: declared in _resolve_routing(), read here.
        # assembler.resolve_truth_mode() is the accessor — orchestrator passes routing.
        truth_mode = resolve_truth_mode(_routing)

        # ── non-agentic tool execution (reserved for future intents) ─────────
        tool_output: str | None = None
        if intent_result.requires_tools and intent_result.intent not in _AGENTIC_INTENTS:
            tool_output = await _run_tool(intent_result, lang)

        # ── answerability gate ────────────────────────────────────────────────
        profile = extract_query_profile(request.user_message, lang)
        clarification_key = _needs_clarification(
            request=request,
            intent_result=intent_result,
            profile=profile,
            retrieved_context=(
                f"{request.vision_context}\n\n{_retrieved_context}".strip()
                if request.vision_context and _retrieved_context
                else request.vision_context or _retrieved_context
            ),
            tool_output=tool_output,
        )
        if clarification_key:
            logger.info("Answerability gate: clarification requested", extra={
                "intent": intent_result.intent,
                "reason": clarification_key,
                "query_kind": profile.query_kind,
            })
            return _denied_result(
                reason=clarification_key,
                lang=lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── STRICT truth gate ─────────────────────────────────────────────────
        # TruthMode.STRICT + no grounding data → deny rather than hallucinate.
        has_grounding = bool(_retrieved_context) or bool(tool_output)
        if truth_mode == TruthMode.STRICT and not has_grounding:
            logger.info("Truth gate: STRICT with no grounding data", extra={
                "intent": intent_result.intent,
                "domain": _routing.domain_hint,
            })
            deny_reason = "no_grounded_data"
            if intent_result.intent == Intent.SEARCH:
                deny_reason = _SEARCH_NEED_MORE_CLUES
            elif intent_result.intent in (Intent.WEATHER, Intent.MAPS, Intent.MAPS_ROUTE, Intent.MAPS_POI):
                deny_reason = _LIVE_DATA_UNAVAILABLE
            return _denied_result(
                reason=deny_reason,
                lang=lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── estimate ─────────────────────────────────────────────────────────
        _fast_token_threshold = 300
        _estimate_tier = (
            Tier.FAST
            if request.complexity == Complexity.LOW and request.input_tokens < _fast_token_threshold
            else Tier.GENERAL
        )
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            _estimate_tier,
        )
        # Include lc_transformer overhead for CRITICAL requests above 32K tokens.
        # lc_transformer activates inside _run_heavy() — EPK can't know its actual
        # cost yet, so we add a conservative estimate here to avoid allowing requests
        # the user cannot afford. See economic.md §5 (DEBT-A1).
        _LC_TOKEN_THRESHOLD = 32_000
        _lc_estimate_tokens = (
            request.input_tokens
            if request.complexity == Complexity.CRITICAL and request.input_tokens > _LC_TOKEN_THRESHOLD
            else 0
        )
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=_estimate_tier,
            embedding_type=request.embedding_type,
            lc_transformer_input_tokens=_lc_estimate_tokens,
        )

        # ── EPK ──────────────────────────────────────────────────────────────
        epk_out = evaluate(EPKInput(
            estimated_cost=estimated,
            user_balance=request.user_balance,
            complexity=request.complexity,
        ))

        logger.info("EPK", extra={
            "request_id":     _rid,
            "decision":       epk_out.decision,
            "estimated_cost": f"{estimated:.6f}",
        })
        increment(f"epk.decision.{epk_out.decision.value.lower()}")
        gauge("epk.last_estimated_cost", estimated)

        # Publish EPK decision event — non-blocking, fire-and-forget.
        _epk_event_name = {
            EPKDecision.ALLOW:          EventName.EPK_ALLOW,
            EPKDecision.DENY:           EventName.EPK_DENY,
            EPKDecision.DEGRADED_MODE:  EventName.EPK_DEGRADE,
            EPKDecision.HEAVY_REQUIRED: EventName.EPK_ALLOW,  # HEAVY is an ALLOW variant
        }.get(epk_out.decision, EventName.EPK_ALLOW)
        try:
            await event_bus.publish(EPKDecisionEvent(
                name=_epk_event_name,
                user_id=None,  # user_id not propagated to orchestrator — enriched upstream
                payload={
                    "decision":       epk_out.decision.value,
                    "estimated_cost": estimated,
                    "user_balance":   request.user_balance,
                    "request_id":     request.request_id,
                },
            ))
        except Exception as _epk_ev_exc:
            logger.debug("EPKDecisionEvent publish failed", extra={"error": str(_epk_ev_exc)})

        if epk_out.decision == EPKDecision.DENY:
            return _denied_result(
                reason="insufficient_balance",
                lang=lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── tier ─────────────────────────────────────────────────────────────
        tier = select_tier(estimated)

        # ── assemble retrieved context ────────────────────────────────────────
        retrieved_context = _retrieved_context or ""
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        # ── build messages with truth mode ────────────────────────────────────
        messages = _build_messages(request, intent_result, retrieved_context, truth_mode, tier)

        logger.info("Truth mode", extra={
            "mode": truth_mode,
            "has_context": bool(retrieved_context),
        })

        # ── EPK signal execution ──────────────────────────────────────────────
        if epk_out.decision == EPKDecision.HEAVY_REQUIRED:
            return await _run_heavy(request, intent_result, messages, epk_out.decision, lang)

        if epk_out.decision == EPKDecision.DEGRADED_MODE:
            return await _run_degraded(request, intent_result, messages, epk_out.decision, lang)

        return await _run_allow(request, intent_result, messages, tier, epk_out.decision, lang)

    except Exception as exc:
        logger.error("Pipeline crashed", extra={"error": str(exc)}, exc_info=True)
        synthesis = synthesize(SynthesisInput(
            raw_text="",
            intent=None,
            tier=Tier.FAST,
            denied=True,
            deny_reason="default_deny",
            lang=lang,
        ))
        return OrchestratorResult(
            text=synthesis.text,
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=_empty_usage(request),
            denied=True,
            deny_reason="internal_error",
            lang=lang,
        )
# ─── INTERNAL HELPERS for orchestrator pipeline ──────────────────────────────

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_history_tokens(history: list[dict] | None) -> int:
    if not history:
        return 0
    return sum(_estimate_tokens(t.get("content", "")) for t in history)


def _classify_complexity_internal(text: str) -> Complexity:
    """
    Classify message complexity for EPK cost estimation.
    Moved from update_handler to orchestrator — orchestration decision.
    """
    stripped = text.strip()
    length = len(stripped)
    has_code = "```" in stripped
    has_json = "{" in stripped and "}" in stripped and ":" in stripped

    if has_code and has_json:
        return Complexity.CRITICAL
    elif has_code or has_json:
        return Complexity.HIGH
    elif length > 800:
        return Complexity.MEDIUM
    return Complexity.LOW


async def _run_safety_gate_pass1(text: str, request_id: str = "") -> int:
    """Safety Gate Pass 1 — NON-BLOCKING observability. Returns tokens_used."""
    try:
        import asyncio

        from security.safety_gate import check_pass1
        gate1 = await asyncio.wait_for(check_pass1(text), timeout=8.0)
        return gate1.tokens_used
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 1 timeout", extra={"request_id": request_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 1 crashed", extra={"error": str(exc)})
    return 0


async def _run_safety_gate_pass2(text: str, request_id: str = "") -> tuple[int, int, int]:
    """Safety Gate Pass 2 — NON-BLOCKING observability. Returns (pass2_tokens, safeguard_in, safeguard_out)."""
    try:
        import asyncio

        from security.safety_gate import check_pass2
        gate2 = await asyncio.wait_for(check_pass2(text), timeout=12.0)
        return gate2.tokens_used, gate2.safeguard_tokens_used, gate2.safeguard_output_tokens_used
    except asyncio.TimeoutError:
        logger.warning("Safety Gate Pass 2 timeout", extra={"request_id": request_id})
    except Exception as exc:
        logger.error("Safety Gate Pass 2 crashed", extra={"error": str(exc)})
    return 0, 0, 0


async def _run_multilingual(text: str, lang: str) -> tuple[str, int, int, str]:
    """
    Multilingual normalization — LLM agent, lives in orchestrator (§34).
    Returns (normalized_text, input_tokens, output_tokens, model_used).
    """
    try:
        from llm.multilingual_preprocessor import PreprocessorInput
        from llm.multilingual_preprocessor import preprocess as ml_preprocess
        ml_result = await ml_preprocess(PreprocessorInput(text=text, lang=lang))
        if ml_result.was_normalized:
            logger.info("Multilingual normalization applied", extra={
                "model": ml_result.model_used, "lang": lang,
            })
            return ml_result.text, ml_result.input_tokens, ml_result.output_tokens, ml_result.model_used
        return text, ml_result.input_tokens, ml_result.output_tokens, ml_result.model_used
    except Exception as exc:
        logger.warning("Multilingual preprocessor failed (non-critical)", extra={"error": str(exc)})
    return text, 0, 0, "passthrough"


async def _load_history(
    supabase, user_id: int, complexity: Complexity, message_tokens: int, input_type: str
) -> tuple[list[dict] | None, object]:
    """
    Load conversation history. Returns (history, history_store).
    Orchestrator owns history: load here, save after response.
    """
    if supabase is None or input_type == "image_group":
        return None, None

    from memory.conversation_history import (
        FAST_HISTORY_BUDGET,
        GENERAL_HISTORY_BUDGET,
        ConversationHistory,
    )
    budget = (
        FAST_HISTORY_BUDGET
        if complexity == Complexity.LOW and message_tokens < 300
        else GENERAL_HISTORY_BUDGET
    )
    try:
        store = ConversationHistory(supabase)
        history = await store.get_history(user_id, token_budget=budget)
        logger.info("History loaded", extra={
            "user_id": user_id, "turns": len(history), "budget": budget,
        })
        return history, store
    except Exception as exc:
        logger.error("History load failed", extra={"error": str(exc)})
    return None, None


async def _run_retrieval(
    supabase, redis, hf_client, text: str, user_id: int
) -> tuple[str, int, int]:
    """
    pgvector + reranker retrieval. Returns (retrieved_context, embedding_tokens, rerank_tokens).
    """
    if supabase is None:
        logger.warning("Retrieval skipped — Supabase unavailable")
        return "", 0, 0

    if redis is None:
        logger.warning("Retrieval: Redis unavailable — running without cache")

    try:
        from contracts.retrieval_contracts import RetrievalQuery
        from memory.supabase_store import SupabaseStore
        from retrieval.retrieval_engine import RetrievalEngine

        engine_kwargs: dict = {"supabase_store": SupabaseStore(supabase)}
        if redis is not None:
            from retrieval.cache.embedding_cache import EmbeddingCache
            from retrieval.cache.query_cache import QueryCache
            from retrieval.cache.rerank_cache import RerankCache
            engine_kwargs["query_cache"]     = QueryCache(redis)
            engine_kwargs["embedding_cache"] = EmbeddingCache(redis)
            engine_kwargs["rerank_cache"]    = RerankCache(redis)

        engine = RetrievalEngine(**engine_kwargs)
        retrieval_result = await engine.retrieve(RetrievalQuery(
            text=text,
            user_id=str(user_id),
            top_k=5,
        ))

        if retrieval_result.documents:
            from context.assembler import assemble
            from context.serializer import to_prompt_string
            from contracts.context_contracts import ContextRequest

            _MIN_SCORE = 0.75
            relevant = [
                d for d in retrieval_result.documents
                if d.content and d.score >= _MIN_SCORE
            ]

            # assemble() applies char-budget truncation and separators.
            # to_prompt_string() converts AssembledContext → str for the prompt.
            assembled = assemble(ContextRequest(documents=relevant))
            context = to_prompt_string(assembled)

            logger.info("Retrieval done", extra={
                "docs": len(retrieval_result.documents),
                "relevant": len(relevant),
                "assembled_chars": assembled.document_count,
                "truncated": assembled.truncated,
                "emb_tokens": retrieval_result.embedding_tokens,
                "rerank_tokens": retrieval_result.rerank_tokens,
            })
            return context, retrieval_result.embedding_tokens, retrieval_result.rerank_tokens

    except Exception as exc:
        logger.warning("Retrieval failed", extra={"error": str(exc)})

    return "", 0, 0


async def _save_history(
    history_store, user_id: int, user_message: str, response_text: str,
    vision_caption: str = "",
) -> None:
    """Save conversation turn. Orchestrator owns history lifecycle."""
    if history_store is None:
        return
    try:
        _msg = vision_caption if vision_caption.strip() else user_message
        await history_store.append(user_id, "user", _msg)
        if response_text:
            await history_store.append(user_id, "assistant", response_text)
    except Exception as exc:
        logger.error("History save failed", extra={"error": str(exc)})


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    """
    Full pipeline entry point. Orchestrator owns everything except
    transport I/O (Telegram parsing, ASR, TTS, send).

    Pipeline (architecture.md §4):
      Safety Gate Pass 1  [NON-BLOCKING observability]
      Feature Extraction  [complexity classification]
      Multilingual        [LLM normalization — agent, billed]
      Safety Gate Pass 2  [NON-BLOCKING observability]
      History load
      Retrieval
      EPK
      → _run_allow / _run_degraded / _run_heavy
      History save
    """
    lang = request.lang or "en"
    _rid = request.request_id or ""

    logger.info("Orchestrator start", extra={
        "request_id": _rid,
        "message_len": len(request.user_message),
        "lang": lang,
        "balance": request.user_balance,
    })

    increment("orchestrator.requests")
    _run_start = __import__("time").perf_counter()

    # Pipeline state — populated as stages run
    _safety_pass1_tokens         = 0
    _safety_pass2_tokens         = 0
    _safety_safeguard_tokens     = 0
    _safety_safeguard_out_tokens = 0
    _ml_input_tokens             = 0
    _ml_output_tokens            = 0
    _ml_model                    = "passthrough"
    _history_store               = None
    _conversation_history: list[dict] | None = None
    _retrieved_context           = ""
    _embedding_tokens            = 0
    _rerank_tokens               = 0
    _embedding_type              = "large"

    try:
        text = request.user_message

        # ── Safety Gate Pass 1 — NON-BLOCKING (architecture §21) ─────────────
        _safety_pass1_tokens = await _run_safety_gate_pass1(text, _rid)

        # ── Feature Extraction ────────────────────────────────────────────────
        complexity = _classify_complexity_internal(text)
        _message_tokens = _estimate_tokens(text)

        logger.debug("Complexity", extra={"complexity": complexity, "length": len(text)})

        # ── Multilingual normalization (LLM agent — §34) ──────────────────────
        text, _ml_input_tokens, _ml_output_tokens, _ml_model = await _run_multilingual(text, lang)

        # ── Safety Gate Pass 2 — NON-BLOCKING (architecture §21) ─────────────
        _safety_pass2_tokens, _safety_safeguard_tokens, _safety_safeguard_out_tokens = (
            await _run_safety_gate_pass2(text, _rid)
        )

        # ── meta/analysis.py — pre-reasoning hints (§4) ──────────────────────
        _analysis_report = None
        try:
            from meta.analysis import analyse as _analyse
            _analysis_report = _analyse(text, lightweight=False)
        except Exception as exc:
            logger.warning("analysis.py failed (non-critical)", extra={"error": str(exc)})

        # ── History load (orchestrator owns history lifecycle) ────────────────
        _conversation_history, _history_store = await _load_history(
            supabase=request.supabase,
            user_id=request.user_id,
            complexity=complexity,
            message_tokens=_message_tokens,
            input_type=request.input_type,
        )

        # ── Token estimation ──────────────────────────────────────────────────
        _history_tokens = _estimate_history_tokens(_conversation_history)
        input_tokens    = _message_tokens + _history_tokens

        logger.info("Pipeline ready", extra={
            "request_id":    _rid,
            "input_tokens":  input_tokens,
            "complexity":    complexity,
            "history_turns": len(_conversation_history) if _conversation_history else 0,
        })

        # ── Retrieval ─────────────────────────────────────────────────────────
        _retrieved_context, _embedding_tokens, _rerank_tokens = await _run_retrieval(
            supabase=request.supabase,
            redis=request.redis,
            hf_client=request.hf_client,
            text=text,
            user_id=request.user_id,
        )

        # ── Build internal request for execution paths ─────────────────────────
        # Execution paths still use the rich internal request shape.
        # We construct it here now that all pipeline data is available.
        _internal = _InternalRequest(
            user_message=text,
            user_balance=request.user_balance,
            input_tokens=input_tokens,
            complexity=complexity,
            retrieved_context=_retrieved_context,
            conversation_history=_conversation_history,
            embedding_tokens=_embedding_tokens,
            rerank_tokens=_rerank_tokens,
            embedding_type=_embedding_type,
            lang=lang,
            has_code_block="```" in text,
            has_json_shape="{" in text and "}" in text and ":" in text,
            context_size=input_tokens,
            vision_intent=request.vision_intent,
            supabase=request.supabase,
            hf_client=request.hf_client,
            input_type=request.input_type,
            request_id=_rid,
            analysis_report=_analysis_report,
            skip_web_search=request.skip_web_search,
            is_vision=request.is_vision,
            vision_context=request.vision_context,
        )

        result = await _run_pipeline(_internal)

        # ── History save ──────────────────────────────────────────────────────
        if not result.denied:
            await _save_history(
                history_store=_history_store,
                user_id=request.user_id,
                user_message=text,
                response_text=result.text,
            )

        # ── Wire pipeline billing fields onto result ──────────────────────────
        _pm = PipelineMetrics(
            safety_pass1_tokens=_safety_pass1_tokens,
            safety_pass2_tokens=_safety_pass2_tokens,
            safety_safeguard_tokens=_safety_safeguard_tokens,
            safety_safeguard_output_tokens=_safety_safeguard_out_tokens,
            multilingual_input_tokens=_ml_input_tokens,
            multilingual_output_tokens=_ml_output_tokens,
            multilingual_model=_ml_model,
        )
        result.pipeline_metrics = _pm

        gauge("orchestrator.last_latency_ms",
              round((__import__("time").perf_counter() - _run_start) * 1000, 2))
        return result

    except Exception as exc:
        logger.error("Orchestrator crashed", extra={"error": str(exc)}, exc_info=True)
        increment("orchestrator.errors")
        gauge("orchestrator.last_latency_ms",
              round((__import__("time").perf_counter() - _run_start) * 1000, 2))
        synthesis = synthesize(SynthesisInput(
            raw_text="", intent=None, tier=Tier.FAST,
            denied=True, deny_reason="default_deny", lang=lang,
        ))
        return OrchestratorResult(
            text=synthesis.text, tier=Tier.FAST, model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=0, output_tokens=0,
                embedding_tokens=0, rerank_tokens=0,
                tier=Tier.FAST, embedding_type="large", llm_cost_usd=0.0,
            ),
            denied=True, deny_reason="internal_error", lang=lang,
        )