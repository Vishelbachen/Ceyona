from __future__ import annotations

import logging
from dataclasses import dataclass

from agents.fast_agent import AgentResult
from llm.groq_client import groq_client
from llm.model_router import CONSENSUS_MODEL, route_max_tokens
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConsensusResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    sources_used: int


def _build_arbitration_prompt(candidates: list[AgentResult]) -> list[dict]:
    """Build prompt for gpt-oss-120b to select and synthesize best answer."""
    numbered = "\n\n".join(
        f"[CANDIDATE {i+1}]\n{r.text.strip()}"
        for i, r in enumerate(candidates)
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a consensus arbitrator. "
                "You will receive multiple candidate responses to the same user query. "
                "Select the most accurate, complete, and safe response. "
                "You may synthesize the best elements from multiple candidates. "
                "Return only the final response — no meta-commentary, no explanation of your choice."
            ),
        },
        {
            "role": "user",
            "content": f"Candidates:\n\n{numbered}",
        },
    ]


async def resolve(candidates: list[AgentResult]) -> ConsensusResult:
    """
    Arbitrate between multiple agent outputs using gpt-oss-120b.

    Activation rule:
      ONLY on ALLOW path (mutex with HEAVY_REQUIRED).
      Never called when Heavy Tier is active.

    Falls back to longest-response heuristic if arbitration fails.
    """
    successful = [r for r in candidates if r.success and r.text.strip()]

    if not successful:
        logger.warning("Consensus: no successful candidates")
        return ConsensusResult(
            text="", model="", input_tokens=0, output_tokens=0, sources_used=0,
        )

    # Single candidate — no arbitration needed
    if len(successful) == 1:
        r = successful[0]
        return ConsensusResult(
            text=r.text,
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            sources_used=1,
        )

    total_input  = sum(r.input_tokens for r in successful)
    total_output = sum(r.output_tokens for r in successful)

    try:
        messages = _build_arbitration_prompt(successful)
        response = await groq_client.complete(
            model=CONSENSUS_MODEL,
            messages=messages,
            max_tokens=route_max_tokens(Tier.HEAVY),
            temperature=0.2,   # low temp — arbitration, not generation
        )

        if response.text.strip():
            logger.info("Consensus arbitrated", extra={
                "sources_used": len(successful),
                "model": CONSENSUS_MODEL,
            })
            return ConsensusResult(
                text=response.text,
                model=CONSENSUS_MODEL,
                input_tokens=total_input + response.input_tokens,
                output_tokens=total_output + response.output_tokens,
                sources_used=len(successful),
            )

    except Exception as exc:
        logger.error("Consensus arbitration failed — using heuristic fallback",
                     extra={"error": str(exc)}, exc_info=True)

    # Heuristic fallback: longest response
    best = max(successful, key=lambda r: len(r.text))
    logger.info("Consensus heuristic fallback", extra={"model": best.model})
    return ConsensusResult(
        text=best.text,
        model=best.model,
        input_tokens=total_input,
        output_tokens=total_output,
        sources_used=len(successful),
    )