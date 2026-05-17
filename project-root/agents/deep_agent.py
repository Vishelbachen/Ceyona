from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.groq_client import groq_client, LLMResponse
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
    Deep agent — groq/compound (Agent Layer, models1.md §6).

    Uses compound directly via groq_client — NOT complete_with_fallback.
    Agent Layer models have tool-selection authority; tier fallback cascade
    is not appropriate here. If compound fails, coordinator handles fallback
    to fast_agent.

    Previously used complete_with_fallback(Tier.GENERAL) which routed to
    llama-3.3-70b-versatile — correct for General Tier but wrong for Agent Layer.
    groq/compound is a distinct capability (multi-step tool-use) not a tier model.
    """
    try:
        response: LLMResponse = await groq_client.complete(
            model=DEEP_AGENT_MODEL,
            messages=messages,
            max_tokens=route_max_tokens(Tier.GENERAL),
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