import logging
from dataclasses import dataclass

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.kernel.cost_model import actual_cost, estimate_cost, estimate_output_tokens
from core.kernel.decision_matrix import select_tier
from core.kernel.execution_policy_kernel import EPKInput, evaluate
from llm.fallback_handler import complete_with_fallback
from llm.groq_client import LLMResponse
from llm.prompt_engine import PromptContext, build_messages
from cognition.intent_engine import classify
from cognition.response_synthesizer import SynthesisInput, synthesize

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


async def run(request: OrchestratorRequest) -> OrchestratorResult:

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
            intent=classify(request.user_message).intent,
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

    # ── step 9: build prompt ─────────────────────────────
    intent_result = classify(request.user_message)

    messages = build_messages(PromptContext(
        user_message=request.user_message,
        system_prompt=request.system_prompt or intent_result.system_prompt,
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

    # ── step 16: synthesize final response ───────────────
    synthesis = synthesize(SynthesisInput(
        raw_text=llm_response.text,
        intent=intent_result.intent,
        tier=tier,
        lang=request.lang,
    ))

    logger.info("Execution complete", extra={
        "tier": tier,
        "model": llm_response.model,
        "cost_usd": cost,
        "output_tokens": llm_response.output_tokens,
        "lang": request.lang,
    })

    return OrchestratorResult(
        text=synthesis.text,
        tier=tier,
        model=llm_response.model,
        epk_decision=epk_out.decision,
        usage=usage,
        lang=request.lang,
    )