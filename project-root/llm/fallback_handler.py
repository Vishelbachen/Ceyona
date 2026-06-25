from __future__ import annotations

import logging

from contracts.shared_types import Tier
from llm.groq_client import LLMResponse, groq_client
from llm.model_router import (
    get_tier_models,
    get_reasoning_effort,
    requires_thinking_disabled,
    route_max_tokens,
)

logger = logging.getLogger(__name__)

_FALLBACK_CASCADE: dict[Tier, Tier | None] = {
    Tier.HEAVY: Tier.GENERAL,
    Tier.GENERAL: Tier.FAST,
    Tier.FAST: None,
}

# When a 413 (Payload Too Large) is hit, keep the tail of the user content —
# that is where the actual question usually lives once retrieved_context has
# been prepended by llm.prompt_engine.build_messages().
_CONTEXT_TRUNCATE_RATIO = 0.5


def _is_413(exc: Exception) -> bool:
    """Return True if exception is a Groq 413 Payload Too Large."""
    msg = str(exc).lower()
    return "413" in msg or "payload too large" in msg or "request too large" in msg


def _clone_messages(messages: list[dict]) -> list[dict]:
    """Return a shallow copy so retries never mutate the caller's payload."""
    return [dict(message) for message in messages]


def _truncate_messages(messages: list[dict]) -> list[dict] | None:
    """
    Shorten the longest user message while preserving the actual question.

    The prompt builder injects retrieved context before the user question,
    so truncating from the front would usually delete the question and keep
    the grounding data. This helper keeps the tail instead.
    """
    longest_idx = -1
    longest_len = 0
    for i, message in enumerate(messages):
        if message.get("role") != "user":
            continue
        content = str(message.get("content", ""))
        if len(content) > longest_len:
            longest_len = len(content)
            longest_idx = i

    if longest_idx == -1 or longest_len < 200:
        return None

    truncated = _clone_messages(messages)
    content = str(truncated[longest_idx].get("content", ""))

    # Preserve the tail of the message: for prompt-engine payloads that
    # means keeping the actual question and dropping the oversized context.
    if "\n\n" in content:
        tail = content.rsplit("\n\n", 1)[-1].strip()
        if tail:
            truncated[longest_idx]["content"] = "[context truncated]\n\n" + tail
        else:
            keep = max(120, int(len(content) * _CONTEXT_TRUNCATE_RATIO))
            truncated[longest_idx]["content"] = "[context truncated]\n" + content[-keep:].lstrip()
    else:
        keep = max(120, int(len(content) * _CONTEXT_TRUNCATE_RATIO))
        truncated[longest_idx]["content"] = "[context truncated]\n" + content[-keep:].lstrip()

    logger.warning(
        "Payload truncated to avoid 413",
        extra={
            "original_chars": longest_len,
            "kept_chars": len(str(truncated[longest_idx]["content"])),
        },
    )
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
      - qwen/qwen3.6-27b: reasoning_effort="none" mandatory (thinking=False was qwen3-32b legacy, now deprecated)
      - response.actual_tier reflects the tier that actually executed,
        which may be lower than the requested tier after cascade.
        Callers MUST use response.actual_tier for billing (not the requested tier).
    """
    current_tier: Tier | None = tier
    current_messages = _clone_messages(messages)

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
            "tier": current_tier,
            "messages": len(current_messages),
            "total_chars": _total_chars,
            "has_context": _has_context,
            "roles": [m.get("role") for m in current_messages],
        })

        for model in models:
            extra_params: dict = {}
            if requires_thinking_disabled(model):
                extra_params["reasoning_effort"] = "none"  # Groq API param for qwen3.6-27b (models.md §27.2); thinking=False is qwen3-32b legacy
                extra_params["top_p"] = 0.80              # models.md §3, §27.2 non-thinking params
                extra_params["presence_penalty"] = 1.5    # models.md §3, §27.2 non-thinking params
                # top_k omitted — not supported by Groq OpenAI-compatible API (models.md §27.2 note)
            else:
                effort = get_reasoning_effort(model, current_tier)
                if effort is not None:
                    extra_params["reasoning_effort"] = effort  # gpt-oss-120b: "high" on HEAVY, "medium" on GENERAL/consensus; gpt-oss-20b: "low" on FAST (models.md §4, §27.1, §27.3)

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
                            "actual_tier": current_tier,
                            "model": model,
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
                        "tier": current_tier,
                        "model": model,
                        "attempt": attempt,
                        "error": str(exc),
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