import logging

from contracts.shared_types import Complexity
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, run
from transport.telegram.message_router import UpdateType, extract_text

logger = logging.getLogger(__name__)

# ─── TOKEN ESTIMATION ────────────────────────────────────────────────────────
# Simple char-based estimate: ~4 chars per token (good enough for EPK gate)

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _classify_complexity(text: str) -> Complexity:
    """
    Structural heuristic — no semantic inference.
    Matches Feature Layer definition from architecture v4.7.
    """
    has_code = "```" in text or "    " in text
    has_json = "{" in text and "}" in text
    length = len(text)

    if has_code and has_json:
        return Complexity.CRITICAL
    if has_code or has_json:
        return Complexity.HIGH
    if length > 500:
        return Complexity.MEDIUM
    return Complexity.LOW


# ─── MAIN HANDLER ────────────────────────────────────────────────────────────

async def handle_message(
    update: dict,
    update_type: UpdateType,
    user_id: int,
    user_balance: float,
) -> OrchestratorResult:
    """
    Process a validated message update through the execution DAG.
    Returns OrchestratorResult — caller is responsible for sending reply.
    """
    text = extract_text(update)

    if not text:
        logger.info("Empty text update ignored", extra={"user_id": user_id})
        from core.execution.orchestrator import OrchestratorResult, UsageRecord
        from contracts.shared_types import EPKDecision, Tier
        return OrchestratorResult(
            text="",
            tier=Tier.FAST,
            model="",
            epk_decision=EPKDecision.DENY,
            usage=UsageRecord(
                input_tokens=0,
                output_tokens=0,
                embedding_tokens=0,
                rerank_tokens=0,
                tier=Tier.FAST,
                embedding_type="large",
                cost_usd=0.0,
            ),
            denied=True,
            deny_reason="empty_message",
        )

    input_tokens = _estimate_tokens(text)
    complexity = _classify_complexity(text)

    logger.info("Handling message", extra={
        "user_id": user_id,
        "input_tokens": input_tokens,
        "complexity": complexity,
    })

    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        input_tokens=input_tokens,
        complexity=complexity,
        # retrieval context injected here in future when retrieval layer is ready
    )

    return await run(request)