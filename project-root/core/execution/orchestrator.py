import logging
from dataclasses import dataclass

from contracts.shared_types import (
    Complexity,
    EPKDecision,
    Tier,
)
from core.kernel.cost_model import (
    actual_cost,
    estimate_cost,
    estimate_output_tokens,
)
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.fallback_handler import complete_with_fallback
from llm.groq_client import LLMResponse
from llm.prompt_engine import PromptContext, build_messages

logger = logging.getLogger(__name__)


# ─── ORCHESTRATOR I/O CONTRACTS ──────────────────────────────────────────────

@dataclass
class OrchestratorRequest:
    user_message: str
    user_balance: float             # USD
    input_tokens: int               # pre-counted by caller
    complexity: Complexity
    system_prompt: str = ""
    retrieved_context: str = ""
    conversation_history: list[dict] | None = None
    embedding_tokens: int = 0
    rerank_tokens: int = 0
    embedding_type: str = "large"


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


# ─── MAIN FLOW ───────────────────────────────────────────────────────────────

async def run(request: OrchestratorRequest) -> OrchestratorResult:
    """
    Execute the full 16-step DAG:

    1.  Feature extraction          ← done upstream, input_tokens provided
    2.  Estimate output tokens
    3.  Estimate cost
    4.  EPK  (ALLOW / DENY / DEGRADE)
    5.  Select tier (decision_matrix)
    6-8. Retrieval / rerank         ← done upstream, tokens provided
    9.  Build prompt (intent_engine / prompt_engine)
    10. Agent execution             ← future layer, bypassed for now
    11. Model routing
    12. LLM execution
    13. Usage meter (actual tokens)
    14. Actual cost
    15. TON deduction               ← future layer
    16. Return result
    """

    # ── step 2: estimate output tokens ───────────────────
    estimated_output = estimate_output_tokens(
        request.input_tokens,
        request.complexity,
        Tier.GENERAL,           # conservative estimate before tier is known
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
        return OrchestratorResult(
            text="",
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
        )

    # ── step 5: select tier ──────────────────────────────
    tier = select_tier(estimated)

    # DEGRADE → force FAST tier
    if epk_out.decision == EPKDecision.DEGRADE:
        tier = Tier.FAST
        logger.info("EPK DEGRADE: forcing FAST tier")

    # ── step 9: build prompt ─────────────────────────────
    messages = build_messages(PromptContext(
        user_message=request.user_message,
        system_prompt=request.system_prompt,
        retrieved_context=request.retrieved_context,
        conversation_history=request.conversation_history,
    ))

    # ── steps 11-12: route + LLM execution ───────────────
    llm_response: LLMResponse = await complete_with_fallback(
        tier=tier,
        messages=messages,
    )

    # ── step 13-14: usage meter + actual cost ────────────
    cost = actual_cost(
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
    )

    usage = UsageRecord(
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        embedding_tokens=request.embedding_tokens,
        rerank_tokens=request.rerank_tokens,
        tier=tier,
        embedding_type=request.embedding_type,
        cost_usd=cost,
    )

    logger.info("Execution complete", extra={
        "tier": tier,
        "model": llm_response.model,
        "cost_usd": cost,
        "output_tokens": llm_response.output_tokens,
    })

    return OrchestratorResult(
        text=llm_response.text,
        tier=tier,
        model=llm_response.model,
        epk_decision=epk_out.decision,
        usage=usage,
    )