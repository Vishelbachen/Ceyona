from __future__ import annotations

import logging
from dataclasses import dataclass

from contracts.shared_types import Tier
from llm.fallback_handler import complete_with_fallback

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    success: bool
    error: str = ""
    actual_tier: str = ""  # tier that actually executed (may differ from requested on cascade)


async def run(messages: list[dict], temperature: float = 0.7, tier: Tier = Tier.GENERAL) -> AgentResult:
    """
    Deep agent — routes via complete_with_fallback using the provided tier.

    Default: Tier.GENERAL → qwen/qwen3.6-27b (primary) → openai/gpt-oss-120b (fallback).
    HEAVY path: Tier.HEAVY → openai/gpt-oss-120b (reasoning_effort="high").
    Tier is passed explicitly from coordinator — never hardcoded here (architecture.md §2.3).

    NOTE: groq/compound is registered as DEEP_AGENT_MODEL in model_router.py
    and is the intended long-term target for this agent (multi-step tool-use).
    It is NOT used here because compound models require Groq tool-use API
    with a `tools` parameter — calling them as plain chat-completion produces
    empty or error responses ("DeepAgent failed" in Sentry).
    Revert to compound when Groq tool-use API stabilises.
    Tracked in: architecture.md §27, models.md §6.
    """
    try:
        response = await complete_with_fallback(
            tier=tier,
            messages=messages,
            temperature=temperature,
        )
        return AgentResult(
            text=response.text,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            success=bool(response.text.strip()),
            actual_tier=response.actual_tier,
        )
    except Exception as exc:
        logger.error("DeepAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="", model="", input_tokens=0, output_tokens=0,
            success=False, error=str(exc),
        )