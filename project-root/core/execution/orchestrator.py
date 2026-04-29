import logging
from dataclasses import dataclass

from cognition.intent_engine import classify
from cognition.multi_agent_coordinator import CoordinationResult, coordinate, plan_agents
from cognition.reasoning_engine import select_strategy
from cognition.response_synthesizer import SynthesisInput, synthesize
from contracts.shared_types import Complexity, EPKDecision, Tier
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.prompt_engine import PromptContext, build_messages

logger = logging.getLogger(__name__)


# ─── CONTRACTS ───────────────────────────────────────────────────────────────

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


# ─── MAIN FLOW ───────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    """
    Full 16-step DAG with agent layer.
    """

    # ── step 1: intent classification ────────────────────
    intent_result = classify(request.user_message)

    # ── step 2: estimate output tokens ───────────────────
    estimated_output = estimate_output_tokens(
        request.input_tokens,
        request.complexity,
        Tier.GENERAL,
    )

    # ── step 3: estimate cost ────────────────────────────
    estimated = estimate_cost(
        input_tokens=request.input_tokens,
        estimated_output_tokens=estimated_output,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=Tier.GENERAL,
        embedding_type=request.embedding_type,
    )

    # ── step 4: EPK ──────────────────────────────────────
    epk_out = evaluate(EPKInput(
        estimated_cost=estimated,
        user_balance=request.user_balance,
    ))

    logger.info("EPK decision", extra={
        "decision": epk_out.decision,
        "estimated_cost": estimated,
        "reason": epk_out.reason,
    })

    if epk_out.decision == EPKDecision.DENY:
        synthesis = synthesize(SynthesisInput(
            raw_text="",
            intent=intent_result.intent,
            tier=Tier.FAST,
            denied=True,
            deny_reason="insufficient_balance",
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
            deny_reason=epk_out.reason,
            lang=request.lang,
        )

    # ── step 5: select tier ──────────────────────────────
    tier = select_tier(estimated)

    if epk_out.decision == EPKDecision.DEGRADE:
        tier = Tier.FAST
        logger.info("EPK DEGRADE: forcing FAST tier")

    # ── step 6: reasoning strategy ───────────────────────
    strategy = select_strategy(intent_result.intent, tier)

    # ── step 7: agent plan ───────────────────────────────
    plan = plan_agents(intent_result.intent, tier, strategy)

    # ── step 8: build prompt ─────────────────────────────
    messages = build_messages(PromptContext(
        user_message=(
            f"{strategy.instruction_prefix} {request.user_message}".strip()
            if strategy.instruction_prefix
            else request.user_message
        ),
        system_prompt=request.system_prompt or intent_result.system_prompt,
        retrieved_context=request.retrieved_context,
        conversation_history=request.conversation_history,
    ))

    # ── steps 9-11: agent execution ──────────────────────
    coordination: CoordinationResult = await coordinate(
        plan=plan,
        messages=messages,
        user_message=request.user_message,
    )

    if coordination.blocked:
        synthesis = synthesize(SynthesisInput(
            raw_text="",
            intent=intent_result.intent,
            tier=tier,
            denied=True,
            deny_reason="default_deny",
            lang=request.lang,
        ))
        return OrchestratorResult(
            text=synthesis.text,
            tier=tier,
            model="",
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
            denied=True,
            deny_reason="safety_block",
            lang=request.lang,
        )

    # ── step 12-13: actual cost ──────────────────────────
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

    # ── step 14: synthesize response ─────────────────────
    synthesis = synthesize(SynthesisInput(
        raw_text=coordination.text,
        intent=intent_result.intent,
        tier=tier,
        lang=request.lang,
    ))

    logger.info("Execution complete", extra={
        "tier": tier,
        "model": coordination.model,
        "cost_usd": cost,
        "output_tokens": coordination.output_tokens,
        "lang": request.lang,
        "intent": intent_result.intent,
        "agent_plan": plan.primary,
    })

    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model=coordination.model,
        epk_decision=epk_out.decision,
        usage=usage,
        lang=request.lang,
    )