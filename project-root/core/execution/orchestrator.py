from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent, IntentResult, classify
from cognition.multi_agent_coordinator import (
    CoordinationResult,
    coordinate,
    plan_agents,
)
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from context.assembler import resolve_truth_mode
from contracts.shared_types import Complexity, EPKDecision, Tier, TruthMode
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.heavy_input_shaper import ShaperInput, shape
from llm.prompt_engine import PromptContext, build_messages
from observability.metrics import gauge, increment
from observability.tracing import trace

logger = logging.getLogger(__name__)

# ─── TRUTH ENFORCEMENT ────────────────────────────────────────────────────────

# Intents for which pre-EPK generic web search MUST NOT be triggered.
# Self-contained intents only — they generate freely without external data.
# Agentic intents (search, weather, maps, maps_poi, maps_route) are NOT here:
# they collect context via explicit intent-specific retrieval (see below).
# Owned here — not in transport layer.
_NO_SEARCH_INTENTS = {
    "creative", "conversation", "emotional", "code", "math",
}

# Intents that require intent-specific retrieval via web_tools.run_tool().
# Each maps to its tool_name in web_tools._TOOL_MAP.
# compound_agent receives the collected context in messages and synthesizes.
_AGENTIC_TOOL_MAP: dict[str, str] = {
    "search":      "search",
    "weather":     "weather",
    "maps":        "maps",
    "maps_poi":    "maps_poi",
    "maps_route":  "maps_route",
}

# Intents that MUST have retrieved context — no context = don't call LLM.
# Agentic intents (WEATHER, MAPS, MAPS_POI, MAPS_ROUTE, SEARCH) ARE included:
# orchestrator now collects their context explicitly before EPK (see below).
# If retrieval fails → STRICT gate fires → no hallucination.
_STRICT_INTENTS: set[Intent] = set()

# All tool intents that go through compound_agent as synthesizer.
# compound_agent no longer executes tools — it receives pre-assembled context
# in messages and synthesizes the final response.
_AGENTIC_INTENTS = {
    Intent.SEARCH,
    Intent.WEATHER,
    Intent.MAPS,
    Intent.MAPS_POI,
    Intent.MAPS_ROUTE,
}

# No-data fallback message key (goes to synthesizer)
_NO_GROUNDED_DATA = "no_grounded_data"


def _needs_grounding(intent: Intent | None) -> bool:
    return intent in _STRICT_INTENTS


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
    # When set, orchestrator skips classify() to avoid a duplicate call.
    vision_intent: IntentResult | None = None
    supabase: object = None
    hf_client: object = None
    # Input type tag — used by update_handler to skip history load for
    # request types where conversation history is irrelevant or actively
    # harmful (e.g. media group albums: each album is a fresh isolated task).
    # Values: "text" (default), "image_group", "voice", "image"
    input_type: str = "text"
    # Fix §10.4: request_id for log correlation across pipeline stages.
    # Format: "{update_id}:{user_id}" — set by webhook, propagated through pipeline.
    # Allows correlating logs from webhook → update_handler → orchestrator → coordinator.
    request_id: str = ""
    # analysis_report: pre-reasoning structural hints from meta/analysis.py (§4 lifecycle).
    # Non-binding — passed to intent_engine.classify() for confidence adjustment only.
    # None when analysis is unavailable (DENY path, error). Never authoritative.
    analysis_report: object = None  # meta.analysis.AnalysisReport | None
    # skip_web_search: True on the vision pipeline path.
    # Reason: vision_handler sends extracted image description as user_message.
    # That description is NOT a valid search query — it must never trigger web_search.
    # Sending image descriptions to Tavily/SerpAPI returns 400 Bad Request.
    # Set to True by update_handler when forwarding a vision result to orchestrator.
    skip_web_search: bool = False
    # is_vision: True when the request originates from the vision pipeline
    # (single photo or album with uncertainty=True that requires pipeline).
    # Used as a routing guard: prevents _classify_complexity() from treating
    # extracted image descriptions as high-complexity user text, which would
    # trigger CHAIN_OF_THOUGHT reasoning mode and produce CoT artefacts
    # ("Проверка ограничений", tables, "OK" lines).
    # Semantic truth: Vision output ≠ User intent.
    # Vision requests must never enter reasoning mode regardless of text length.
    # Set to True by update_handler on the vision pipeline path.
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
    tts_audio_bytes: bytes = b""  # TTS audio — set by update_handler after speech synthesis
                                   # non-empty only when is_voice_input=True and TTS succeeded
                                   # webhook sends sendVoice when this is non-empty
    audio_seconds: float = 0.0    # ASR billing: whisper transcription duration (set by update_handler)
    tts_characters: int = 0        # TTS billing: orpheus character count (set by update_handler)
    tool_calls: int = 0            # compound tool calls executed — billing counter (set by orchestrator)


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


# ─── TOOL RUNNER ──────────────────────────────────────────────────────────────




async def _run_tool(intent_result, lang: str) -> str | None:
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


# ─── PROMPT BUILDER (truth-aware) ────────────────────────────────────────────

def _build_messages(
    request: OrchestratorRequest,
    intent_result,
    retrieved_context: str,
    truth_mode: TruthMode,
    tier: Tier = Tier.GENERAL,
) -> list[dict]:
    # Use real tier so FAST requests get lightweight instruction_prefix,
    # not the heavy GENERAL strategy prompt. Fixes audit §1.3 + §6.3.
    strategy = select_strategy(intent_result.intent, tier)
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
    ))


# ─── EXECUTION PATHS ──────────────────────────────────────────────────────────

async def _run_allow(
    request: OrchestratorRequest,
    intent_result,
    messages: list[dict],
    tier: Tier,
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    strategy = select_strategy(intent_result.intent, tier)
    plan = plan_agents(intent_result.intent, tier, strategy)

    increment(f"orchestrator.tier.{tier.value.lower()}")
    with trace("coordinator", tier=tier.value, intent=str(intent_result.intent)):
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
            temperature=strategy.temperature,
            intent=intent_result.intent,
            lang=lang,
            tier=tier,
        )

    if coordination.blocked:
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

    # Use actual_tier for billing — may be lower than requested tier after cascade.
    # audit.md §3.4 / §9.1: fallback cascade must not overbill at requested tier.
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
        from_vision=request.vision_intent is not None,  # §13.3: force CoT strip on vision path
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
    )


async def _run_degraded(
    request: OrchestratorRequest,
    intent_result,
    messages: list[dict],
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    tier = Tier.FAST
    strategy = select_strategy(intent_result.intent, tier)
    plan = plan_agents(intent_result.intent, tier, strategy)

    increment(f"orchestrator.tier.{tier.value.lower()}")
    with trace("coordinator", tier=tier.value, intent=str(intent_result.intent)):
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
            temperature=strategy.temperature,
            intent=intent_result.intent,
            lang=lang,
            tier=tier,
        )

    if coordination.blocked:
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

    # Use actual_tier for billing — may be lower than requested tier after cascade.
    # audit.md §3.4 / §9.1: fallback cascade must not overbill at requested tier.
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
        from_vision=request.vision_intent is not None,  # §13.3: force CoT strip on vision path
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
    )


async def _run_heavy(
    request: OrchestratorRequest,
    intent_result,
    messages: list[dict],
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    tier = Tier.HEAVY
    strategy = select_strategy(intent_result.intent, tier)

    shaper_result = shape(ShaperInput(
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
        truth_mode = resolve_truth_mode(intent_result.intent)
        messages = build_messages(PromptContext(
            user_message=shaper_result.text,
            system_prompt=request.system_prompt or intent_result.system_prompt,
            retrieved_context=request.retrieved_context or "",
            conversation_history=request.conversation_history,
            truth_mode=truth_mode,
            lang=request.lang,
        ))

    plan = plan_agents(intent_result.intent, tier, strategy)

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        reasoning_plan="",
        temperature=strategy.temperature,
        intent=intent_result.intent,
        lang=lang,
        tier=tier,
    )

    if coordination.blocked:
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

    # Use actual_tier for billing — may be lower than requested tier after cascade.
    # audit.md §3.4 / §9.1: fallback cascade must not overbill at requested tier.
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
        from_vision=request.vision_intent is not None,  # §13.3: force CoT strip on vision path
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
    )


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    lang = request.lang or "en"

    # Propagate request_id to all orchestrator-level logs for pipeline correlation.
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
        # Use pre-computed intent from vision_handler (§15) when available
        # to avoid classifying the same text twice. For all other paths,
        # classify here — single classification, single authority.
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
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
            })

        # ── is_vision routing guard ──────────────────────────────────────────
        # Vision pipeline requests carry extracted image descriptions as
        # user_message. These are LLM-generated text, NOT user intent.
        #
        # Without this guard, _classify_complexity() sees a long structured
        # string ("Изображение 1: ...\nИзображение 2: ...") and returns
        # MEDIUM/HIGH complexity → reasoning_engine selects CHAIN_OF_THOUGHT
        # for ANALYSIS/INSTRUCTION intents → CoT artefacts appear in the
        # response ("Проверка ограничений", tables, pseudo-validation).
        #
        # Fix: force CONVERSATION intent and FAST complexity on vision path.
        # Vision output ≠ user intent — a text classifier must never route it.
        # Semantic contract: the LLM receives the description as text and
        # responds naturally without entering reasoning mode.
        if request.is_vision:
            from cognition.intent_engine import (
                Intent,
                IntentResult,
                build_system_prompt,
            )
            intent_result = IntentResult(
                intent=Intent.CONVERSATION,
                confidence=1.0,
                system_prompt=build_system_prompt(Intent.CONVERSATION, lang),
                requires_retrieval=False,
                requires_tools=False,
            )
            # Override complexity so select_strategy() and plan_agents()
            # always resolve to FAST-equivalent path (DIRECT mode, no CoT).
            # Complexity is already imported at module level (line 15) —
            # no local import needed; local import causes UnboundLocalError
            # on non-vision paths (Python treats name as local in entire scope).
            request = type(request)(**{
                **request.__dict__,
                "complexity": Complexity.LOW,
            })
            logger.info("Vision routing guard applied — forced CONVERSATION + LOW complexity", extra={
                "request_id": _rid,
            })

        # ── retrieval ────────────────────────────────────────────────────────
        # All external data collection happens here, before EPK.
        # Two paths:
        #   (a) Agentic intents (SEARCH, WEATHER, MAPS, MAPS_POI, MAPS_ROUTE):
        #       explicit intent-specific retrieval via web_tools.run_tool().
        #       compound_agent receives the result in messages and synthesizes.
        #   (b) Other retrieval-benefiting intents (QUESTION, ANALYSIS, etc.):
        #       generic web search via Tavily → SerpAPI → SearXNG fallback chain.
        # Self-contained intents (_NO_SEARCH_INTENTS) skip both paths.
        # Vision pipeline requests skip search (image context is not a valid query).
        # Zero-balance users skip search (pre-EPK cost guard).
        _retrieved_context = request.retrieved_context

        _intent_value = intent_result.intent.value
        _can_fetch = (
            not _retrieved_context
            and request.user_balance > 0
            and not request.skip_web_search
        )

        if _can_fetch and _intent_value in _AGENTIC_TOOL_MAP:
            # Path (a): intent-specific retrieval
            _tool_name = _AGENTIC_TOOL_MAP[_intent_value]
            try:
                from external.web_tools import run_tool as _web_run_tool
                _tool_result = await _web_run_tool(
                    tool_name=_tool_name,
                    params={"query": request.user_message, "lang": lang},
                    lang=lang,
                )
                if _tool_result:
                    _retrieved_context = _tool_result
                    logger.info("Agentic retrieval: context acquired", extra={
                        "intent": _intent_value,
                        "tool":   _tool_name,
                        "chars":  len(_tool_result),
                    })
                else:
                    logger.warning("Agentic retrieval: empty result", extra={
                        "intent": _intent_value,
                        "tool":   _tool_name,
                    })
            except Exception as exc:
                logger.warning("Agentic retrieval failed — continuing without", extra={
                    "intent": _intent_value,
                    "tool":   _tool_name,
                    "error":  str(exc),
                })

        elif _can_fetch and _intent_value not in _NO_SEARCH_INTENTS:
            # Path (b): generic web search for non-agentic intents
            try:
                from external.web_tools import run_tool as _web_run_tool
                web_result = await _web_run_tool(
                    tool_name="search",
                    params={"query": request.user_message, "lang": lang},
                    lang=lang,
                )
                if web_result:
                    _retrieved_context = web_result
                    logger.info("Web search: context acquired", extra={
                        "intent": _intent_value,
                        "chars":  len(web_result),
                    })
            except Exception as exc:
                logger.warning("Web search failed — continuing without", extra={"error": str(exc)})

        # ── truth mode ───────────────────────────────────────────────────────
        truth_mode = resolve_truth_mode(intent_result.intent)

        # ── non-agentic tool execution (reserved for future intents) ─────────
        # Agentic intents (WEATHER, MAPS, MAPS_POI, MAPS_ROUTE, SEARCH) collect
        # context above. _run_tool() is kept for future non-agentic tool intents.
        tool_output: str | None = None
        if intent_result.requires_tools and intent_result.intent not in _AGENTIC_INTENTS:
            tool_output = await _run_tool(intent_result, lang)

        # ── STRICT truth gate ─────────────────────────────────────────────────
        # If TruthMode is STRICT and there is no grounding data → deny.
        # Agentic intents are NO LONGER excluded: compound_agent is now a
        # synthesizer, not a self-grounding agent. Grounding is the orchestrator's
        # responsibility. If retrieval failed → gate fires → no hallucination.
        has_grounding = bool(_retrieved_context) or bool(tool_output)
        if truth_mode == TruthMode.STRICT and not has_grounding:
            logger.info("Truth gate: STRICT intent with no grounding data", extra={
                "intent": intent_result.intent,
            })
            return _denied_result(
                reason="no_grounded_data",
                lang=lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── estimate ─────────────────────────────────────────────────────────
        # Adaptive tier for EPK estimation (fixes audit §6.1):
        # Short LOW-complexity requests are estimated at FAST rates (~10x cheaper).
        # Larger or complex requests fall back to GENERAL (conservative, safe overestimate).
        # This prevents legitimate short queries from hitting DEGRADED_MODE.
        _fast_token_threshold = 300  # input tokens below which FAST estimate applies
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