from __future__ import annotations

import logging
from dataclasses import dataclass

from cognition.intent_engine import Intent, classify
from cognition.multi_agent_coordinator import CoordinationResult, coordinate, plan_agents
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from contracts.shared_types import Complexity, EPKDecision, Tier
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.heavy_input_shaper import ShaperInput, shape
from llm.prompt_engine import PromptContext, build_messages

logger = logging.getLogger(__name__)


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

# Intents whose tool output is the FINAL answer — skip LLM entirely.
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


# ─── EXECUTION PATHS ──────────────────────────────────────────────────────────

async def _run_allow(
    request: OrchestratorRequest,
    intent_result,
    messages: list[dict],
    tier: Tier,
    epk_decision: EPKDecision,
    lang: str,
) -> OrchestratorResult:
    """
    ALLOW path: Fast → General → Agents → safety_agent → Consensus.
    Orchestrator executes EPK signal only — no routing decisions.
    """
    strategy = select_strategy(intent_result.intent, tier)
    plan = plan_agents(intent_result.intent, tier, strategy)

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        temperature=strategy.temperature,
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
    """
    DEGRADED_MODE path: Fast Tier only → Response Synthesizer directly.
    Skips: Reasoning / Coordinator / General / Agents / safety_agent /
           heavy_input_shaper / Heavy / Consensus.
    """
    tier = Tier.FAST
    strategy = select_strategy(intent_result.intent, tier)
    plan = plan_agents(intent_result.intent, tier, strategy)

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        temperature=strategy.temperature,
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
    """
    HEAVY_REQUIRED path:
      Skip Fast, skip General.
      heavy_input_shaper (ALWAYS called, self-gated).
      Heavy Tier mandatory.
      safety_agent mandatory.
      Skip Consensus (mutex).
      Response Synthesizer aggregates directly.
    """
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
        retrieved_context = request.retrieved_context or ""
        messages = build_messages(PromptContext(
            user_message=shaper_result.text,
            system_prompt=request.system_prompt or intent_result.system_prompt,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
        ))

    plan = plan_agents(intent_result.intent, tier, strategy)

    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
        reasoning_plan="",
        temperature=strategy.temperature,
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
    """
    EPK signal execution only.
    NO policy generation. NO routing decisions. NO Heavy Tier self-activation.

    DAG:
      Intent → Tool? → Estimate → EPK →
        DENY           → exit
        ALLOW          → _run_allow
        DEGRADED_MODE  → _run_degraded
        HEAVY_REQUIRED → _run_heavy
    """
    lang = request.lang or "en"

    logger.info("Orchestrator start", extra={
        "message_len": len(request.user_message),
        "input_tokens": request.input_tokens,
        "complexity": request.complexity,
        "lang": lang,
        "balance": request.user_balance,
    })

    try:
        # ── intent classification (lang-aware, history-aware) ──────────────────
        intent_result = classify(
            request.user_message,
            lang=lang,
            conversation_history=request.conversation_history,
        )
        logger.info("Intent", extra={
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
        })

        # ── tool execution ────────────────────────────────────────────────────
        tool_output: str | None = None
        if intent_result.requires_tools:
            tool_output = await _run_tool(intent_result, lang)

        # ── estimate output tokens ────────────────────────────────────────────
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            Tier.GENERAL,
        )

        # ── estimate cost ─────────────────────────────────────────────────────
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=Tier.GENERAL,
            embedding_type=request.embedding_type,
        )

        # ── EPK: SOLE POLICY AUTHORITY ────────────────────────────────────────
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

        # ── tier selection ────────────────────────────────────────────────────
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

        # ── prompt construction ───────────────────────────────────────────────
        retrieved_context = request.retrieved_context or ""
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        strategy = select_strategy(intent_result.intent, tier)

        user_message_for_prompt = (
            f"{strategy.instruction_prefix} {request.user_message}".strip()
            if strategy.instruction_prefix
            else request.user_message
        )

        messages = build_messages(PromptContext(
            user_message=user_message_for_prompt,
            system_prompt=request.system_prompt or intent_result.system_prompt,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
        ))

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