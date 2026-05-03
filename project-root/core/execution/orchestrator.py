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
    """Build a denied OrchestratorResult with a localised message."""
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


# ─── INTENT ROUTING CONSTANTS ─────────────────────────────────────────────────

# Intents that require at least GENERAL tier (code quality / accuracy matters)
_HEAVY_INTENTS = {Intent.CODE, Intent.ANALYSIS, Intent.MATH}

# Intents that use external tools and can skip LLM entirely on tool success
_TOOL_INTENTS = {Intent.WEATHER, Intent.SEARCH}


# ─── TOOL RUNNER ──────────────────────────────────────────────────────────────

async def _run_tool(intent_result, lang: str) -> str | None:
    """
    Execute an external tool (weather / search).
    Returns tool output string or None on failure.
    Never raises.
    """
    if not intent_result.requires_tools or not intent_result.tool_name:
        return None

    logger.info(
        "Tool dispatch",
        extra={
            "tool": intent_result.tool_name,
            "params": intent_result.tool_params,
        },
    )

    try:
        from external.web_tools import run_tool
        result = await run_tool(
            tool_name=intent_result.tool_name,
            params=intent_result.tool_params,
            lang=lang,
        )
        logger.info(
            "Tool executed",
            extra={"tool": intent_result.tool_name, "result_len": len(result) if result else 0},
        )
        return result
    except Exception as exc:
        logger.error(
            "Tool execution failed",
            extra={"tool": intent_result.tool_name, "error": str(exc)},
            exc_info=True,
        )
        return None


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    """
    Full execution pipeline. EPK signal execution only.

    Steps:
      1. Intent classification (language-aware)
      2. Tool execution (weather / search) — if applicable
      3. Estimate output tokens
      4. Estimate cost
      5. EPK decision (ALLOW / DENY / DEGRADE)
      6. Tier selection
      7. Reasoning strategy selection
      8. Agent plan selection
      9. Prompt construction
      10. Agent coordination (with fallback)
      11. Actual cost calculation
      12. Response synthesis

    On any unrecoverable failure: returns localised error, never empty text.
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
        # ── step 1: intent (lang-aware) ───────────────────────────────────────
        intent_result = classify(request.user_message, lang=lang)
        logger.info("Intent", extra={
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "requires_tools": intent_result.requires_tools,
        })

        # ── step 2: tool execution ────────────────────────────────────────────
        tool_output: str | None = None
        if intent_result.requires_tools:
            tool_output = await _run_tool(intent_result, lang)

        # ── step 3: estimate output tokens ────────────────────────────────────
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            Tier.GENERAL,
        )

        # ── step 4: estimate cost ─────────────────────────────────────────────
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=Tier.GENERAL,
            embedding_type=request.embedding_type,
        )

        # ── step 5: EPK ───────────────────────────────────────────────────────
        epk_out = evaluate(EPKInput(
            estimated_cost=estimated,
            user_balance=request.user_balance,
        ))

        logger.info("EPK", extra={
            "decision": epk_out.decision,
            "estimated_cost": f"{estimated:.6f}",
            "balance": request.user_balance,
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

        # ── step 6: tier selection ────────────────────────────────────────────
        tier = select_tier(estimated)

        if epk_out.decision == EPKDecision.DENY:
            # Already handled above — guard only
            pass
        elif epk_out.decision == EPKDecision.DEGRADE:
            tier = Tier.FAST
            logger.info("EPK DEGRADE → FAST tier")
        elif intent_result.intent in _HEAVY_INTENTS and tier == Tier.FAST:
            # Code / Math / Analysis always get at least GENERAL for quality
            tier = Tier.GENERAL
            logger.info(
                "Intent upgrade FAST → GENERAL",
                extra={"intent": intent_result.intent},
            )

        # ── step 7: reasoning strategy ────────────────────────────────────────
        strategy = select_strategy(intent_result.intent, tier)

        # ── step 8: agent plan ────────────────────────────────────────────────
        plan = plan_agents(intent_result.intent, tier, strategy)

        # ── step 9: prompt construction ───────────────────────────────────────
        # Inject tool output into context if available
        retrieved_context = request.retrieved_context or ""
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        # Tool-only intents: skip LLM entirely when tool succeeded
        if intent_result.intent in _TOOL_INTENTS and tool_output:
            logger.info("Tool-only path — skipping LLM", extra={"intent": intent_result.intent})
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

        # Use the language-aware system prompt from intent_engine
        system_prompt = request.system_prompt or intent_result.system_prompt

        user_message_for_prompt = (
            f"{strategy.instruction_prefix} {request.user_message}".strip()
            if strategy.instruction_prefix
            else request.user_message
        )

        messages = build_messages(PromptContext(
            user_message=user_message_for_prompt,
            system_prompt=system_prompt,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
        ))

        logger.debug("Prompt built", extra={"message_count": len(messages)})

        # ── step 10: agent coordination ───────────────────────────────────────
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
        )

        logger.info("Coordination", extra={
            "blocked": coordination.blocked,
            "block_reason": coordination.block_reason,
            "text_len": len(coordination.text),
            "model": coordination.model,
        })

        # Forward the actual block_reason from coordinator (not hardcoded)
        if coordination.blocked:
            block_reason = coordination.block_reason or "default_deny"
            return _denied_result(
                reason=block_reason,
                lang=lang,
                tier=tier,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=epk_out.decision,
            )

        # ── step 11: actual cost ──────────────────────────────────────────────
        cost = actual_cost(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=tier,
            embedding_type=request.embedding_type,
        )

        usage = UsageRecord(
            input_tokens=coordination.input_tokens,
            output_tokens=coordination.output_tokens,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=tier,
            embedding_type=request.embedding_type,
            cost_usd=cost,
        )

        # ── step 12: synthesis (final output authority) ───────────────────────
        synthesis = synthesize(SynthesisInput(
            raw_text=coordination.text,
            intent=intent_result.intent,
            tier=tier,
            lang=lang,
        ))

        logger.info("Orchestrator complete", extra={
            "tier": tier,
            "model": coordination.model,
            "cost_usd": f"{cost:.6f}",
            "output_len": len(synthesis.text),
        })

        return OrchestratorResult(
            text=synthesis.text,
            tier=tier,
            model=coordination.model,
            epk_decision=epk_out.decision,
            usage=usage,
            lang=lang,
        )

    except Exception as exc:
        # Catch-all: orchestrator must never crash silently
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
