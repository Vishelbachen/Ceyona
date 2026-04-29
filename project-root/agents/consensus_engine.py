import logging
from dataclasses import dataclass

from agents.fast_agent import AgentResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConsensusResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    sources_used: int


def resolve(results: list[AgentResult]) -> ConsensusResult:
    """
    Select best result from multiple agent outputs.
    Strategy: longest successful response wins.
    Pure function. No I/O. No LLM calls.
    """
    successful = [r for r in results if r.success and r.text.strip()]

    if not successful:
        logger.warning("Consensus: no successful results, using fallback")
        return ConsensusResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            sources_used=0,
        )

    # primary heuristic: longest response = most complete answer
    best = max(successful, key=lambda r: len(r.text))

    total_input = sum(r.input_tokens for r in successful)
    total_output = sum(r.output_tokens for r in successful)

    logger.info("Consensus resolved", extra={
        "sources_used": len(successful),
        "best_model": best.model,
        "best_length": len(best.text),
    })

    return ConsensusResult(
        text=best.text,
        model=best.model,
        input_tokens=total_input,
        output_tokens=total_output,
        sources_used=len(successful),
    )