import logging
from dataclasses import dataclass

from llm.groq_client import groq_client
from llm.model_router import route_model, route_max_tokens
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


async def run(messages: list[dict]) -> AgentResult:
    """
    Creative agent — GENERAL tier, high temperature for creativity.
    Used for: creative writing, storytelling, poetry.
    """
    try:
        response = await groq_client.complete(
            model=route_model(Tier.GENERAL),
            messages=messages,
            max_tokens=route_max_tokens(Tier.GENERAL),
            temperature=0.9,
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