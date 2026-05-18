from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.fallback_handler import complete_with_fallback
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    success: bool
    error: str = ""


async def run(messages: list[dict], temperature: float = 0.7) -> AgentResult:
    """
    Deep agent — Tier.GENERAL via complete_with_fallback (models1.md §6).

    Routing: llama-3.3-70b-versatile → qwen/qwen3-32b → openai/gpt-oss-20b.
    Uses complete_with_fallback — full General Tier cascade with 413 protection
    and qwen thinking=False enforcement.

    NOTE: groq/compound is registered as DEEP_AGENT_MODEL in model_router.py
    and is the intended long-term target for this agent (multi-step tool-use).
    It is NOT used here because compound models require Groq tool-use API
    with a `tools` parameter — calling them as plain chat-completion produces
    empty or error responses ("DeepAgent failed" in Sentry).
    Revert to compound when Groq tool-use API stabilises.
    Tracked in: architecture.md §27, models1.md §6.
    """
    try:
        response = await complete_with_fallback(
            tier=Tier.GENERAL,
            messages=messages,
            temperature=temperature,
        )
        return AgentResult(
            text=response.text,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            success=bool(response.text.strip()),
        )
    except Exception as exc:
        logger.error("DeepAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="", model="", input_tokens=0, output_tokens=0,
            success=False, error=str(exc),
        )