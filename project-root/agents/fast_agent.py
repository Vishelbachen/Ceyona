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
    Fast agent — llama-3.1-8b-instant (Fast Tier, models.md).

    Used for: conversation, simple questions, emotional responses,
    low-cost tasks, fallback for synthesis.

    Calls complete_with_fallback(Tier.FAST) so it cascades to GENERAL
    if llama-3.1-8b-instant is unavailable, never returning empty silently.
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
        )
    except Exception as exc:
        logger.error("FastAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="", model="", input_tokens=0, output_tokens=0,
            success=False, error=str(exc),
        )