from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent, IntentResult, classify
from cognition.multi_agent_coordinator import CoordinationResult, coordinate, plan_agents
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from context.assembler import resolve_truth_mode
from contracts.shared_types import Complexity, EPKDecision, Tier, TruthMode
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.heavy_input_shaper import ShaperInput, shape
from llm.prompt_engine import PromptContext, build_messages

logger = logging.getLogger(__name__)

# ─── TRUTH ENFORCEMENT ────────────────────────────────────────────────────────

# Intents that MUST have retrieved context — no context = don't call LLM
_STRICT_INTENTS = {
    Intent.SEARCH,
    Intent.WEATHER,
    Intent.MAPS,
    Intent.MAPS_POI,
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
    # Optional pre-computed intent (e.g. from vision_handler).
    # When set, orchestrator skips classify() to avoid duplicate work.
    forced_intent: IntentResult | None = None


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

_TOOL_INTENTS = {Intent.WEATHER, Intent.SEARCH, Intent.MAPS, Intent.MAPS_POI}


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
) -> list[dict]:
    strategy = select_strategy(intent_result.intent, Tier.GENERAL)
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

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        temperature=strategy.temperature,
        intent=intent_result.intent,
        lang=lang,
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

    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
    )

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
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
            tier=tier,
            embedding_type=request.embedding_type,
            cost_usd=cost,
        ),
        lang=lang,
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

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        temperature=strategy.temperature,
        intent=intent_result.intent,
        lang=lang,
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

    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
    )

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
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
            tier=tier,
            embedding_type=request.embedding_type,
            cost_usd=cost,
        ),
        lang=lang,
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

    cost = actual_cost(
        input_tokens=coordination.input_tokens,
        output_tokens=coordination.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
    )

    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=lang,
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
            tier=tier,
            embedding_type=request.embedding_type,
            cost_usd=cost,
        ),
        lang=lang,
    )


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    lang = request.lang or "en"

    logger.info("Orchestrator start", extra={
        "message_len": len(request.user_message),
        "input_tokens": request.input_tokens,
        "complexity": request.complexity,
        "lang": lang,
        "balance": request.user_balance,
    })

    try:
        # ── intent ───────────────────────────────────────────────────────────
        # Use pre-computed intent when available (e.g. from vision pipeline)
        # to avoid classifying the same text twice.
        if request.forced_intent is not None:
            intent_result = request.forced_intent
            logger.info("Intent (forced)", extra={
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
            })
        else:
            intent_result = classify(
                request.user_message,
                lang=lang,
                conversation_history=request.conversation_history,
            )
            logger.info("Intent", extra={
                "intent": intent_result.intent,
                "confidence": intent_result.confidence,
            })

        # ── truth mode ───────────────────────────────────────────────────────
        truth_mode = resolve_truth_mode(intent_result.intent)

        # ── STRICT: block if no context and no tool output available yet ─────
        # (tool output comes next — we check after tool execution below)

        # ── tool execution ───────────────────────────────────────────────────
        tool_output: str | None = None
        if intent_result.requires_tools:
            tool_output = await _run_tool(intent_result, lang)

        # ── STRICT truth gate ─────────────────────────────────────────────────
        # For STRICT intents: if no retrieved context AND no tool output → block
        has_grounding = bool(request.retrieved_context) or bool(tool_output)
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
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            Tier.GENERAL,
        )
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=Tier.GENERAL,
            embedding_type=request.embedding_type,
        )

        # ── EPK ──────────────────────────────────────────────────────────────
        epk_out = evaluate(EPKInput(
            estimated_cost=estimated,
            user_balance=request.user_balance,
        ))

        logger.info("EPK", extra={
            "decision": epk_out.decision,
            "estimated_cost": f"{estimated:.6f}",
        })

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

        # ── tool-only path ────────────────────────────────────────────────────
        if intent_result.intent in _TOOL_INTENTS and tool_output:
            logger.info("Tool-only path", extra={"intent": intent_result.intent})
            synthesis = synthesize(SynthesisInput(
                raw_text=tool_output,
                intent=intent_result.intent,
                tier=tier,
                lang=lang,
            ))
            return OrchestratorResult(
                text=synthesis.text,
                tier=tier,
                model="tool",
                epk_decision=epk_out.decision,
                usage=_empty_usage(request, tier),
                lang=lang,
            )

        # ── assemble retrieved context ────────────────────────────────────────
        retrieved_context = request.retrieved_context or ""
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        # ── build messages with truth mode ────────────────────────────────────
        messages = _build_messages(request, intent_result, retrieved_context, truth_mode)

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