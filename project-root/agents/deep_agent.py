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


async def run(messages: list[dict], temperature: float = 0.7) -> AgentResult:
    """
    Deep agent — HEAVY tier, multi-step reasoning.
    Used for: code, analysis, math, complex questions.
    """
    try:
        response = await complete_with_fallback(
            tier=Tier.HEAVY,
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
        logger.error("DeepAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            success=False,
            error=str(exc),
        )