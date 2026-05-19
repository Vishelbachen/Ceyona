from __future__ import annotations

import logging

from contracts.shared_types import Tier
from llm.groq_client import groq_client, LLMResponse
from llm.model_router import get_tier_models, requires_thinking_disabled, route_max_tokens

logger = logging.getLogger(__name__)

_FALLBACK_CASCADE: dict[Tier, Tier | None] = {
    Tier.HEAVY:   Tier.GENERAL,
    Tier.GENERAL: Tier.FAST,
    Tier.FAST:    None,
}

# When a 413 (Payload Too Large) is hit, truncate the retrieved_context portion
# of the messages by this fraction and retry once before giving up on the model.
_CONTEXT_TRUNCATE_RATIO = 0.5


def _is_413(exc: Exception) -> bool:
    """Return True if exception is a Groq 413 Payload Too Large."""
    msg = str(exc).lower()
    return "413" in msg or "payload too large" in msg or "request too large" in msg


def _truncate_messages(messages: list[dict]) -> list[dict] | None:
    """
    Shorten the longest non-system message by _CONTEXT_TRUNCATE_RATIO.
    Targets the assistant's retrieved_context injection (always the longest user turn).
    Returns None if there is nothing left to truncate.
    """
    # Find the longest user message (most likely to carry bloated context)
    longest_idx = -1
    longest_len = 0
    for i, m in enumerate(messages):
        if m.get("role") == "user" and len(m.get("content", "")) > longest_len:
            longest_len = len(m["content"])
            longest_idx = i

    if longest_idx == -1 or longest_len < 200:
        return None  # nothing meaningful to truncate

    truncated = list(messages)
    content = truncated[longest_idx]["content"]
    keep = int(len(content) * _CONTEXT_TRUNCATE_RATIO)
    truncated[longest_idx] = dict(truncated[longest_idx])
    truncated[longest_idx]["content"] = content[:keep] + "\n[context truncated]"
    logger.warning("Payload truncated to avoid 413", extra={
        "original_chars": longest_len,
        "kept_chars":     keep,
    })
    return truncated


async def complete_with_fallback(
    tier: Tier,
    messages: list[dict],
    max_retries: int = 1,
    temperature: float = 0.7,
) -> LLMResponse:
    """
    Attempt LLM completion with automatic fallback.

    Order:
      1. Try all models within the requested tier (primary first)
      2. If a 413 is returned → truncate context and retry ONCE before moving on
      3. If all fail → cascade to next lower tier and repeat
      4. Raises RuntimeError if all tiers and all models exhausted

    Special handling:
      - qwen/qwen3-32b: thinking mode explicitly disabled at call site
      - response.actual_tier reflects the tier that actually executed,
        which may be lower than the requested tier after cascade.
        Callers MUST use response.actual_tier for billing (not the requested tier).
    """
    current_tier: Tier | None = tier
    current_messages = messages

    while current_tier is not None:
        models = get_tier_models(current_tier)
        max_tokens = route_max_tokens(current_tier)

        # Log what actually reaches the model — critical for grounding debug
        _total_chars = sum(len(str(m.get("content", ""))) for m in current_messages)
        _has_context = any(
            "SEARCH RESULTS" in str(m.get("content", "")) or
            "## CONTEXT" in str(m.get("content", ""))
            for m in current_messages
        )
        logger.info("LLM dispatch", extra={
            "tier":        current_tier,
            "messages":    len(current_messages),
            "total_chars": _total_chars,
            "has_context": _has_context,
            "roles":       [m.get("role") for m in current_messages],
        })

        for model in models:
            extra_params: dict = {}
            if requires_thinking_disabled(model):
                extra_params["thinking"] = False

            for attempt in range(max_retries + 1):
                try:
                    response = await groq_client.complete(
                        model=model,
                        messages=current_messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        **extra_params,
                    )
                    if current_tier != tier:
                        logger.warning("Cascade used lower tier for billing", extra={
                            "requested_tier": tier,
                            "actual_tier":    current_tier,
                            "model":          model,
                        })
                    from dataclasses import replace
                    return replace(response, actual_tier=current_tier)
                except Exception as exc:
                    if _is_413(exc):
                        truncated = _truncate_messages(current_messages)
                        if truncated is not None:
                            logger.warning("413 received — retrying with truncated context", extra={
                                "tier": current_tier, "model": model,
                            })
                            current_messages = truncated
                            try:
                                response = await groq_client.complete(
                                    model=model,
                                    messages=current_messages,
                                    max_tokens=max_tokens,
                                    temperature=temperature,
                                    **extra_params,
                                )
                                from dataclasses import replace
                                return replace(response, actual_tier=current_tier)
                            except Exception as exc2:
                                logger.warning("LLM call failed after truncation", extra={
                                    "tier": current_tier, "model": model, "error": str(exc2),
                                })
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

        next_tier = _FALLBACK_CASCADE[current_tier]
        if next_tier:
            logger.warning("Cascading to lower tier", extra={
                "from": current_tier, "to": next_tier,
            })
        current_tier = next_tier

    raise RuntimeError("All LLM tiers and models exhausted. No response available.")