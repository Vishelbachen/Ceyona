from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

import agents.creative_agent as creative_agent
import agents.deep_agent as deep_agent
import agents.fast_agent as fast_agent
from agents.consensus_engine import ConsensusResult, resolve
from agents.fast_agent import AgentResult
from agents.safety_agent import SafetyResult, check as safety_check
from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


# ─── AGENT IDENTIFIERS ────────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST     = "fast"
    DEEP     = "deep"
    CREATIVE = "creative"
    SAFETY   = "safety"


# ─── PLAN CONTRACT ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    fallback: AgentType | None          # used when primary fails
    validators: list[AgentType] = field(default_factory=list)
    use_consensus: bool = False
    parallel: bool = False


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass
class CoordinationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    blocked: bool = False
    block_reason: str = ""


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select which agents to activate based on intent + tier + strategy.
    Pure function. No I/O. No state. No LLM calls.

    Fallback rules:
      - FAST tier primary always falls back to FAST (retry with same agent)
      - DEEP primary falls back to FAST (cheaper, always available)
      - CREATIVE primary falls back to FAST
    """
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=AgentType.FAST,   # retry is the only option at this tier
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            fallback=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,   # if heavy fails, still return something
            validators=[AgentType.FAST, AgentType.SAFETY],
            use_consensus=True,
            parallel=True,
        )

    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if intent in (Intent.CODE, Intent.MATH, Intent.ANALYSIS):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    # default: GENERAL tier, non-special intent
    return AgentPlan(
        primary=AgentType.FAST,
        fallback=None,
        validators=[AgentType.SAFETY],
        use_consensus=False,
        parallel=False,
    )


# ─── AGENT DISPATCHER ─────────────────────────────────────────────────────────

async def _run_agent(agent_type: AgentType, messages: list[dict]) -> AgentResult:
    """
    Dispatch to the correct agent module.
    Never raises — returns AgentResult(success=False) on any error.
    """
    try:
        if agent_type == AgentType.FAST:
            return await fast_agent.run(messages)
        if agent_type == AgentType.DEEP:
            return await deep_agent.run(messages)
        if agent_type == AgentType.CREATIVE:
            return await creative_agent.run(messages)
    except Exception as exc:
        logger.error(
            "Agent dispatch error",
            extra={"agent": agent_type, "error": str(exc)},
            exc_info=True,
        )
    # safety_agent is always a sync check — not dispatched as an LLM agent
    return AgentResult(text="", model="", input_tokens=0, output_tokens=0, success=False)


def _agent_succeeded(result: AgentResult) -> bool:
    return result.success and bool(result.text.strip())


# ─── MAIN COORDINATOR ─────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
) -> CoordinationResult:
    """
    Execute agent plan and return CoordinationResult to orchestrator.

    Execution order:
      1. Safety check (sync, no LLM)
      2. Primary agent
      3. Fallback agent (if primary fails and fallback is configured)
      4. Consensus (HEAVY tier only)

    GUARANTEE: If blocked=False, text is always non-empty.
               If blocked=True, orchestrator renders the deny message.
    """

    # ── 1. safety check (sync, no LLM) ───────────────────────────────────────
    safety: SafetyResult = safety_check(user_message)
    if not safety.safe:
        logger.warning("Safety block", extra={"reason": safety.reason})
        return CoordinationResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            blocked=True,
            block_reason="safety_block",
        )

    # ── 2. primary agent ──────────────────────────────────────────────────────
    primary_result = await _run_agent(plan.primary, messages)

    # ── 3. consensus path (HEAVY tier) ────────────────────────────────────────
    if plan.use_consensus:
        validator_types = [v for v in plan.validators if v != AgentType.SAFETY]

        if plan.parallel and validator_types:
            tasks = [_run_agent(vt, messages) for vt in validator_types]
            validator_results: list[AgentResult] = await asyncio.gather(*tasks)
        else:
            validator_results = []
            for vt in validator_types:
                validator_results.append(await _run_agent(vt, messages))

        # Filter to only successful results; include primary if it succeeded
        candidates = [r for r in [primary_result, *validator_results] if _agent_succeeded(r)]

        if candidates:
            consensus: ConsensusResult = resolve(candidates)
            return CoordinationResult(
                text=consensus.text,
                model=consensus.model,
                input_tokens=consensus.input_tokens,
                output_tokens=consensus.output_tokens,
            )

        # All consensus agents failed — fall through to fallback logic below
        logger.warning("All consensus agents failed — attempting fallback")

    # ── 4. primary succeeded ──────────────────────────────────────────────────
    if _agent_succeeded(primary_result):
        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            input_tokens=primary_result.input_tokens,
            output_tokens=primary_result.output_tokens,
        )

    # ── 5. primary failed → try fallback ──────────────────────────────────────
    logger.warning(
        "Primary agent failed",
        extra={
            "agent": plan.primary,
            "success": primary_result.success,
            "text_len": len(primary_result.text),
            "error": primary_result.error,
        },
    )

    if plan.fallback is not None and plan.fallback != plan.primary:
        logger.info("Trying fallback agent", extra={"agent": plan.fallback})
        fallback_result = await _run_agent(plan.fallback, messages)

        if _agent_succeeded(fallback_result):
            logger.info("Fallback agent succeeded")
            return CoordinationResult(
                text=fallback_result.text,
                model=fallback_result.model,
                input_tokens=fallback_result.input_tokens,
                output_tokens=fallback_result.output_tokens,
            )

        logger.error(
            "Fallback agent also failed",
            extra={"agent": plan.fallback, "error": fallback_result.error},
        )

    # ── 6. all agents failed — return blocked so orchestrator renders error ───
    logger.error("All agents failed — returning blocked result")
    return CoordinationResult(
        text="",
        model="",
        input_tokens=0,
        output_tokens=0,
        blocked=True,
        block_reason="no_response",
    )
