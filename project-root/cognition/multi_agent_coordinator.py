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


# ─── AGENT IDENTIFIERS ───────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST     = "fast_agent"
    DEEP     = "deep_agent"
    CREATIVE = "creative_agent"
    SAFETY   = "safety_agent"


# ─── AGENT PLAN ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    validators: list[AgentType] = field(default_factory=list)
    use_consensus: bool = False
    parallel: bool = False


# ─── COORDINATION RESULT ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class CoordinationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    blocked: bool = False
    block_reason: str = ""


# ─── PLAN SELECTION ──────────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select which agents to activate.
    Pure function. No I/O. No state. No LLM calls.
    """
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.FAST, AgentType.SAFETY],
            use_consensus=True,
            parallel=True,
        )

    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    if intent in (Intent.CODE, Intent.MATH, Intent.ANALYSIS):
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    return AgentPlan(
        primary=AgentType.FAST,
        validators=[AgentType.SAFETY],
        use_consensus=False,
        parallel=False,
    )


# ─── AGENT DISPATCHER ────────────────────────────────────────────────────────

async def _run_agent(agent_type: AgentType, messages: list[dict]) -> AgentResult:
    """Dispatch to the correct agent module."""
    if agent_type == AgentType.FAST:
        return await fast_agent.run(messages)
    if agent_type == AgentType.DEEP:
        return await deep_agent.run(messages)
    if agent_type == AgentType.CREATIVE:
        return await creative_agent.run(messages)
    # safety_agent is always sync check — never dispatched as LLM agent
    return AgentResult(text="", model="", input_tokens=0, output_tokens=0, success=False)


# ─── MAIN COORDINATOR ────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
) -> CoordinationResult:
    """
    Execute agent plan and return final result.
    Handles: safety check, parallel/sequential execution, consensus.
    """

    # ── safety check first (always sync, no LLM) ────────
    safety: SafetyResult = safety_check(user_message)
    if not safety.safe:
        logger.warning("Safety block", extra={"reason": safety.reason})
        return CoordinationResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
            blocked=True,
            block_reason=safety.reason,
        )

    # ── primary agent execution ──────────────────────────
    primary_result = await _run_agent(plan.primary, messages)

    # ── consensus path (HEAVY tier) ──────────────────────
    if plan.use_consensus:
        validator_types = [v for v in plan.validators if v != AgentType.SAFETY]

        if plan.parallel and validator_types:
            tasks = [_run_agent(vt, messages) for vt in validator_types]
            validator_results: list[AgentResult] = await asyncio.gather(*tasks)
        else:
            validator_results = []
            for vt in validator_types:
                validator_results.append(await _run_agent(vt, messages))

        all_results = [primary_result, *validator_results]
        consensus: ConsensusResult = resolve(all_results)

        return CoordinationResult(
            text=consensus.text,
            model=consensus.model,
            input_tokens=consensus.input_tokens,
            output_tokens=consensus.output_tokens,
        )

    # ── single agent path ────────────────────────────────
    if not primary_result.success or not primary_result.text.strip():
        logger.warning("Primary agent failed, no fallback available")
        return CoordinationResult(
            text="",
            model="",
            input_tokens=0,
            output_tokens=0,
        )

    return CoordinationResult(
        text=primary_result.text,
        model=primary_result.model,
        input_tokens=primary_result.input_tokens,
        output_tokens=primary_result.output_tokens,
    )