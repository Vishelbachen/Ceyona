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


# intents that always need GENERAL tier minimum
_HEAVY_INTENTS = {Intent.CODE, Intent.ANALYSIS, Intent.MATH}
_TOOL_INTENTS = {Intent.WEATHER, Intent.SEARCH}


async def _run_tool(intent_result, lang: str) -> str | None:
    if not intent_result.requires_tools or not intent_result.tool_name:
        return None

    logger.error("TOOL DEBUG: name=%s params=%s requires_tools=%s",
                 intent_result.tool_name,
                 intent_result.tool_params,
                 intent_result.requires_tools)

    try:
        from external.web_tools import run_tool
        result = await run_tool(
            tool_name=intent_result.tool_name,
            params=intent_result.tool_params,
            lang=lang,
        )
        logger.info("Tool executed OK", extra={
            "tool": intent_result.tool_name,
            "result": result[:100] if result else None,
        })
        return result
    except Exception as exc:
        import traceback
        logger.error("Tool execution failed FULL: %s\n%s",
                     str(exc),
                     traceback.format_exc())
        return None


async def run(request: OrchestratorRequest) -> OrchestratorResult:
    logger.info("Orchestrator start", extra={
        "user_message_len": len(request.user_message),
        "input_tokens": request.input_tokens,
        "complexity": request.complexity,
        "lang": request.lang,
    })

    try:
        # ── step 1: intent ────────────────────────────────
        intent_result = classify(request.user_message)
        logger.info("Intent classified", extra={
            "intent": intent_result.intent,
            "requires_tools": intent_result.requires_tools,
            "tool_name": intent_result.tool_name,
        })

        # ── step 2: tool execution (weather/search) ───────
        tool_output: str | None = None
        if intent_result.requires_tools:
            tool_output = await _run_tool(intent_result, request.lang)
            logger.info("Tool output", extra={
                "has_output": tool_output is not None,
                "len": len(tool_output) if tool_output else 0,
            })

        # ── step 3: estimate output tokens ───────────────
        estimated_output = estimate_output_tokens(
            request.input_tokens,
            request.complexity,
            Tier.GENERAL,
        )

        # ── step 4: estimate cost ─────────────────────────
        estimated = estimate_cost(
            input_tokens=request.input_tokens,
            estimated_output_tokens=estimated_output,
            embedding_tokens=request.embedding_tokens,
            rerank_tokens=request.rerank_tokens,
            tier=Tier.GENERAL,
            embedding_type=request.embedding_type,
        )

        # ── step 5: EPK ───────────────────────────────────
        epk_out = evaluate(EPKInput(
            estimated_cost=estimated,
            user_balance=request.user_balance,
        ))

        logger.info("EPK decision", extra={
            "decision": epk_out.decision,
            "estimated_cost": estimated,
            "balance": request.user_balance,
        })

        if epk_out.decision == EPKDecision.DENY:
            return _denied_result(
                reason="insufficient_balance",
                lang=request.lang,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=EPKDecision.DENY,
            )

        # ── step 6: select tier ───────────────────────────
        tier = select_tier(estimated)

        if epk_out.decision == EPKDecision.DEGRADE:
            tier = Tier.FAST
            logger.info("EPK DEGRADE: forcing FAST tier")
        elif intent_result.intent in _HEAVY_INTENTS:
            # code/math/analysis always get at least GENERAL
            if tier == Tier.FAST:
                tier = Tier.GENERAL
                logger.info("Intent upgrade: FAST → GENERAL", extra={
                    "intent": intent_result.intent,
                })

        # ── step 7: reasoning strategy ────────────────────
        strategy = select_strategy(intent_result.intent, tier)

        # ── step 8: agent plan ────────────────────────────
        plan = plan_agents(intent_result.intent, tier, strategy)

        # ── step 9: build prompt ──────────────────────────
        # inject tool output into context if available
        retrieved_context = request.retrieved_context
        if tool_output:
            retrieved_context = (
                f"{tool_output}\n\n{retrieved_context}".strip()
                if retrieved_context
                else tool_output
            )

        # for tool-only intents (weather/search) skip LLM if tool succeeded
        if intent_result.intent in _TOOL_INTENTS and tool_output:
            logger.info("Tool-only response, skipping LLM")
            synthesis = synthesize(SynthesisInput(
                raw_text=tool_output,
                intent=intent_result.intent,
                tier=tier,
                lang=request.lang,
            ))
            return OrchestratorResult(
                text=synthesis.text,
                tier=tier,
                model="tool",
                epk_decision=epk_out.decision,
                usage=UsageRecord(
                    input_tokens=request.input_tokens,
                    output_tokens=0,
                    embedding_tokens=request.embedding_tokens,
                    rerank_tokens=request.rerank_tokens,
                    tier=tier,
                    embedding_type=request.embedding_type,
                    cost_usd=0.0,
                ),
                lang=request.lang,
            )

        messages = build_messages(PromptContext(
            user_message=(
                f"{strategy.instruction_prefix} {request.user_message}".strip()
                if strategy.instruction_prefix
                else request.user_message
            ),
            system_prompt=request.system_prompt or intent_result.system_prompt,
            retrieved_context=retrieved_context,
            conversation_history=request.conversation_history,
        ))

        logger.info("Messages built", extra={"message_count": len(messages)})

        # ── step 10: agent execution ──────────────────────
        coordination: CoordinationResult = await coordinate(
            plan=plan,
            messages=messages,
            user_message=request.user_message,
        )

        logger.info("Coordination done", extra={
            "blocked": coordination.blocked,
            "text_len": len(coordination.text),
        })

        if coordination.blocked:
            return _denied_result(
                reason="default_deny",
                lang=request.lang,
                tier=tier,
                input_tokens=request.input_tokens,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                embedding_type=request.embedding_type,
                epk_decision=epk_out.decision,
            )

        # ── step 11: actual cost ──────────────────────────
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

        # ── step 12: synthesize ───────────────────────────
        synthesis = synthesize(SynthesisInput(
            raw_text=coordination.text,
            intent=intent_result.intent,
            tier=tier,
            lang=request.lang,
        ))

        logger.info("Orchestrator complete", extra={
            "tier": tier,
            "model": coordination.model,
            "cost_usd": cost,
            "output_tokens": coordination.output_tokens,
        })

        return OrchestratorResult(
            text=synthesis.text,
            tier=tier,
            model=coordination.model,
            epk_decision=epk_out.decision,
            usage=usage,
            lang=request.lang,
        )

    except Exception as exc:
        logger.error("Orchestrator crashed", extra={"error": str(exc)}, exc_info=True)
        synthesis = synthesize(SynthesisInput(
            raw_text="",
            intent=None,
            tier=Tier.FAST,
            denied=True,
            deny_reason="default_deny",
            lang=request.lang,
        ))
        return OrchestratorResult(
            text=synthesis.text,
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=request.input_tokens,
                output_tokens=0,
                embedding_tokens=request.embedding_tokens,
                rerank_tokens=request.rerank_tokens,
                tier=Tier.FAST,
                embedding_type=request.embedding_type,
                cost_usd=0.0,
            ),
            denied=True,
            deny_reason="internal_error",
            lang=request.lang,
        )