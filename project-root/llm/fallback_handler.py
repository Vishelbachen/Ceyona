import logging
from contracts.shared_types import Tier
from llm.groq_client import groq_client, LLMResponse
from llm.model_router import route_model, route_max_tokens

logger = logging.getLogger(__name__)

# Fallback cascade: if tier fails → try next lower tier
_FALLBACK_CASCADE: dict[str, str | None] = {
    Tier.HEAVY:   Tier.GENERAL,
    Tier.GENERAL: Tier.FAST,
    Tier.FAST:    None,           # no further fallback
}


async def complete_with_fallback(
    tier: Tier,
    messages: list[dict],
    max_retries: int = 1,
) -> LLMResponse:
    """
    Attempt LLM completion with automatic tier fallback on failure.
    Tries current tier, then cascades down if all retries exhausted.
    Raises RuntimeError if all tiers fail.
    """
    current_tier: str | None = tier

    while current_tier is not None:
        model = route_model(current_tier)
        max_tokens = route_max_tokens(current_tier)

        for attempt in range(max_retries + 1):
            try:
                return await groq_client.complete(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.warning(
                    "LLM call failed",
                    extra={
                        "tier": current_tier,
                        "model": model,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                if attempt == max_retries:
                    break

        # cascade to lower tier
        next_tier = _FALLBACK_CASCADE[current_tier]
        if next_tier:
            logger.warning(
                "Falling back to lower tier",
                extra={"from": current_tier, "to": next_tier},
            )
        current_tier = next_tier

    raise RuntimeError("All LLM tiers exhausted. No response available.")