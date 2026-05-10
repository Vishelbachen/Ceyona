from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.groq_client import groq_client
from llm.model_router import DEEP_AGENT_MODEL, route_max_tokens
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
    Deep agent — groq/compound (Agent Layer, models.md).

    Role: tool selection authority, multi-step execution.
    NOT a tier model — compound has tool-use capability beyond
    what Heavy Tier models provide directly.

    Used for: code, analysis, math, complex multi-step tasks.
    """
    try:
        response = await groq_client.complete(
            model=DEEP_AGENT_MODEL,
            messages=messages,
            max_tokens=route_max_tokens(Tier.HEAVY),
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