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


async def run(messages: list[dict]) -> AgentResult:
    """
    Fast agent — single LLM call, FAST tier, no overhead.
    Used for: conversation, simple questions, low-cost tasks.
    """
    try:
        response = await complete_with_fallback(
            tier=Tier.FAST,
            messages=messages,
        )
        return AgentResult(
            text=response.text,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            success=True,
        )
    except Exception as exc:
        logger.error("FastAgent failed", extra={"error": str(exc)})
        return AgentResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            success=False,
            error=str(exc),
        )