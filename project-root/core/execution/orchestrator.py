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
from i18n.t import t
from llm.heavy_input_shaper import ShaperInput, shape
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
    # Pre-computed intent from vision_handler (§15 ingress adapter).
    # Set ONLY on the vision pipeline path — never from transport logic.
    vision_intent: IntentResult | None = None
    supabase: object = None
    hf_client: object = None
    # Input type tag — used by update_handler to skip history load for
    # request types where conversation history is irrelevant or actively
    # harmful (e.g. media group albums).
    # Values: "text" (default), "image_group", "voice", "image"
    input_type: str = "text"
    # request_id for log correlation across pipeline stages.
    # Format: "{update_id}:{user_id}" — set by webhook, propagated through pipeline.
    request_id: str = ""
    # analysis_report: pre-reasoning structural hints from meta/analysis.py (§4 lifecycle).
    # Non-binding — passed to intent_engine.classify() for confidence adjustment only.
    analysis_report: object = None  # meta.analysis.AnalysisReport | None
    # skip_web_search: True on the vision pipeline path.
    # Vision descriptions are NOT valid search queries.
    skip_web_search: bool = False
    # is_vision: True when the request originates from the vision pipeline.
    # Forces CONVERSATION intent + LOW complexity to prevent CoT artefacts.
    is_vision: bool = False


@dataclass
class UsageRecord:
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    rerank_tokens: int
    tier: Tier
    embedding_type: str
    cost_usd: float


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
    tool_calls: int = 0
    resolved_model: str = ""  # preferred_model resolved at routing time (models.md §25.3)


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
            cost_usd=0.0,
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
        cost_usd=0.0,
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
            cost_usd=0.0,
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
            cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model=intent_result.routing.preferred_model or "",
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

    _billing_tier = coordination.actual_tier or tier
    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=_billing_tier,
        embedding_type=request.embedding_type,
    )

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
            cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model="",  # DEGRADED_MODE: no preferred_model — FAST tier is always gpt-oss-20b
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
            from llm.long_context_transformer import transform as _lc_transform
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

    shaper_result = await shape(ShaperInput(
        text=request.user_message,
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
            retrieved_context=request.retrieved_context or "",
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
    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=_billing_tier,
        embedding_type=request.embedding_type,
    )

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
            cost_usd=cost,
        ),
        lang=lang,
        intent=intent_result.intent.value,
        tool_used=bool(intent_result.tool_name),
        tool_calls=coordination.tool_calls,
        resolved_model=intent_result.routing.preferred_model or "",
    )


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
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

    increment("orchestrator.requests")
    _run_start = __import__("time").perf_counter()

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
            retrieved_context=_retrieved_context,
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
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=_estimate_tier,
            embedding_type=request.embedding_type,
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
        logger.error("Orchestrator crashed", extra={"error": str(exc)}, exc_info=True)
        increment("orchestrator.errors")
        gauge("orchestrator.last_latency_ms", round((__import__("time").perf_counter() - _run_start) * 1000, 2))
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