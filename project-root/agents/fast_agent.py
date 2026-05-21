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
    tool_calls: int = 0   # compound tool calls executed (web_search, get_weather, geocode)


async def run(messages: list[dict], temperature: float = 0.7) -> AgentResult:
    """
    Fast agent — Tier.FAST via complete_with_fallback (models1.md §6).

    Routing: llama-3.1-8b-instant (primary, Fast Tier).
    Uses complete_with_fallback — standard tier cascade with 413 protection.

    NOTE: groq/compound-mini is registered as FAST_AGENT_MODEL in model_router.py
    and is the intended long-term target for this agent (tool-use authority).
    It is NOT used here because compound models require Groq tool-use API
    with a `tools` parameter — calling them as plain chat-completion produces
    empty or error responses ("DeepAgent failed" / "FastAgent failed" in Sentry).
    Revert to compound-mini when Groq tool-use API stabilises.
    Tracked in: architecture.md §27, models1.md §6.
    """
    try:
        response = await complete_with_fallback(
            tier=Tier.FAST,
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
        logger.error("FastAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="", model="", input_tokens=0, output_tokens=0,
            success=False, error=str(exc),
        )