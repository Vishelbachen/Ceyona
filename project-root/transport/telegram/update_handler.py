import logging

from contracts.shared_types import Complexity, EPKDecision, Tier
from core.execution.orchestrator import OrchestratorRequest, OrchestratorResult, UsageRecord, run
from transport.telegram.message_router import UpdateType, extract_text

logger = logging.getLogger(__name__)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _classify_complexity(text: str) -> Complexity:
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


async def handle_message(
    update: dict,
    update_type: UpdateType,
    user_id: int,
    user_balance: float,
    lang: str = "en",
) -> OrchestratorResult:
    text = extract_text(update)

    if not text:
        logger.info("Empty text update ignored", extra={"user_id": user_id})
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
            lang=lang,
        )

    input_tokens = _estimate_tokens(text)
    complexity = _classify_complexity(text)

    logger.info("Handling message", extra={
        "user_id": user_id,
        "input_tokens": input_tokens,
        "complexity": complexity,
        "lang": lang,
    })

    request = OrchestratorRequest(
        user_message=text,
        user_balance=user_balance,
        input_tokens=input_tokens,
        complexity=complexity,
        lang=lang,
    )

    return await run(request)