from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.groq_client import groq_client, LLMResponse
from llm.model_router import FAST_AGENT_MODEL, route_max_tokens
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
    Fast agent — groq/compound-mini (Agent Layer, models1.md §6).

    Uses compound-mini directly via groq_client — NOT complete_with_fallback.
    Agent Layer models have tool-selection authority; tier fallback cascade
    is not appropriate here. If compound-mini fails, coordinator handles fallback.

    Previously used complete_with_fallback(Tier.FAST) which routed to
    llama-3.1-8b-instant — correct for Fast Tier but wrong for Agent Layer.
    compound-mini is a distinct capability (tool-use) not a tier replacement.
    """
    try:
        response: LLMResponse = await groq_client.complete(
            model=FAST_AGENT_MODEL,
            messages=messages,
            max_tokens=route_max_tokens(Tier.FAST),
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