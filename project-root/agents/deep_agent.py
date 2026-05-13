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
    Deep agent — llama-3.3-70b-versatile primary, gpt-oss-120b fallback (models.md).

    Used for: code, analysis, math, search synthesis, route queries,
    POI synthesis, complex multi-step tasks.

    Calls complete_with_fallback(Tier.GENERAL) which:
      1. Tries llama-3.3-70b-versatile
      2. Falls back to qwen/qwen3-32b (thinking disabled)
      3. Falls back to openai/gpt-oss-20b
      4. Cascades to FAST tier if all GENERAL models fail
    Never returns empty silently — raises RuntimeError only when
    all tiers exhausted, which coordinator catches as success=False.
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