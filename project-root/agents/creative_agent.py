from __future__ import annotations

import logging

from agents.fast_agent import AgentResult
from contracts.shared_types import Tier
from llm.fallback_handler import complete_with_fallback

logger = logging.getLogger(__name__)


async def run(messages: list[dict], temperature: float = 0.9) -> AgentResult:
    """
    Creative agent — GENERAL tier, high temperature for creativity.
    Used for: creative writing, storytelling, poetry.
    Resilient across all GENERAL tier models via fallback_handler.
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
            success=True,
        )
    except Exception as exc:
        logger.error("CreativeAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            success=False,
            error=str(exc),
        )