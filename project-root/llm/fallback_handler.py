from __future__ import annotations

import logging

from contracts.shared_types import Tier
from llm.groq_client import groq_client, LLMResponse
from llm.model_router import get_tier_models, requires_thinking_disabled, route_max_tokens

logger = logging.getLogger(__name__)

# Fallback cascade: if ALL models in tier fail → try next lower tier
_FALLBACK_CASCADE: dict[Tier, Tier | None] = {
    Tier.HEAVY:   Tier.GENERAL,
    Tier.GENERAL: Tier.FAST,
    Tier.FAST:    None,
}


async def complete_with_fallback(
    tier: Tier,
    messages: list[dict],
    max_retries: int = 1,
) -> LLMResponse:
    """
    Attempt LLM completion with automatic fallback.

    Order:
      1. Try all models within the requested tier (primary first)
      2. If all fail → cascade to next lower tier and repeat
      3. Raises RuntimeError if all tiers and all models exhausted

    Special handling:
      - qwen/qwen3-32b: thinking mode explicitly disabled at call site
    """
    current_tier: Tier | None = tier

    while current_tier is not None:
        models = get_tier_models(current_tier)
        max_tokens = route_max_tokens(current_tier)

        for model in models:
            extra_params: dict = {}
            if requires_thinking_disabled(model):
                extra_params["thinking"] = False

            for attempt in range(max_retries + 1):
                try:
                    return await groq_client.complete(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        **extra_params,
                    )
                except Exception as exc:
                    logger.warning("LLM call failed", extra={
                        "tier":    current_tier,
                        "model":   model,
                        "attempt": attempt,
                        "error":   str(exc),
                    })
                    if attempt == max_retries:
                        break

            logger.warning("Model exhausted — trying next in tier", extra={
                "tier": current_tier, "model": model,
            })

        # All models in tier exhausted → cascade down
        next_tier = _FALLBACK_CASCADE[current_tier]
        if next_tier:
            logger.warning("Cascading to lower tier", extra={
                "from": current_tier, "to": next_tier,
            })
        current_tier = next_tier

    raise RuntimeError("All LLM tiers and models exhausted. No response available.")