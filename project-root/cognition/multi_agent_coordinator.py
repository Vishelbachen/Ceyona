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
from agents.safety_agent import SafetyInput, SafetyResult, SafetyVerdict, check as safety_check
from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from i18n.t import t as _t
from contracts.shared_types import Tier

logger = logging.getLogger(__name__)


# ─── AGENT IDENTIFIERS ────────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST     = "fast"
    DEEP     = "deep"
    CREATIVE = "creative"


# ─── PLAN CONTRACT ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    fallback: AgentType | None
    use_consensus: bool = False
    parallel_validators: list[AgentType] = field(default_factory=list)
    temperature: float = 0.7


# ─── RESULT CONTRACT ──────────────────────────────────────────────────────────

@dataclass
class CoordinationResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    blocked: bool = False
    block_reason: str = ""
    actual_tier: str = ""  # tier that actually executed (may be lower than requested on cascade)


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select agent plan based on intent + tier + strategy.
    Pure function. No I/O. No state. No LLM calls.
    NO policy authority. NO routing decisions.

    HEAVY_REQUIRED tier:
      primary=DEEP, no consensus (mutex), no Fast validators.
    ALLOW tier:
      Fast → General → Agents → safety_agent → Consensus.
    DEGRADED_MODE:
      Fast only (orchestrator routes here directly, plan is minimal).
    """
    # HEAVY_REQUIRED — consensus is skipped (mutex with Heavy Tier)
    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # DEGRADED_MODE — Fast only
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # ALLOW — GENERAL tier
    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    if intent in (Intent.CODE, Intent.MATH, Intent.ANALYSIS, Intent.QUESTION, Intent.INSTRUCTION):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # Tool-result synthesis intents — need DEEP to properly synthesise
    # external data (search snippets, route data, weather) into a coherent answer.
    # Previously fell through to default FAST with no fallback:
    #   FAST agent (llama-3.1-8b, 512 tokens) received 5 search snippets +
    #   system prompt → context overflow or empty response → coordinator blocked.
    if intent in (
        Intent.SEARCH,
        Intent.WEATHER,
        Intent.MAPS,
        Intent.MAPS_POI,
        Intent.MAPS_ROUTE,
    ):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # EMOTIONAL — fast, warm, low temperature for natural empathetic tone
    if intent == Intent.EMOTIONAL:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=None,
            use_consensus=False,
            parallel_validators=[],
            temperature=0.85,
        )

    # default GENERAL — FAST for conversation, search results, etc.
    return AgentPlan(
        primary=AgentType.FAST,
        fallback=None,
        use_consensus=False,
        parallel_validators=[],
        temperature=strategy.temperature,
    )


# ─── AGENT DISPATCHER ─────────────────────────────────────────────────────────

async def _run_agent(
    agent_type: AgentType,
    messages: list[dict],
    temperature: float,
) -> AgentResult:
    """
    Dispatch to the correct agent module based on AgentType.
    Returns AgentResult. Never raises — catches all exceptions and returns
    a failed AgentResult so the coordinator can handle fallback/blocking.
    """
    try:
        if agent_type == AgentType.DEEP:
            return await deep_agent.run(messages=messages, temperature=temperature)
        if agent_type == AgentType.CREATIVE:
            return await creative_agent.run(messages=messages, temperature=temperature)
        # FAST is the default
        return await fast_agent.run(messages=messages, temperature=temperature)
    except Exception as exc:
        logger.error(
            "_run_agent failed",
            extra={"agent": agent_type, "error": str(exc)},
        )
        return AgentResult(text="", model="", input_tokens=0, output_tokens=0, success=False, error=str(exc))


async def _verify_math_solution(
    user_message: str,
    solution: str,
    messages: list[dict],
    temperature: float = 0.1,
) -> tuple[bool, str]:
    """
    Self-verification step for MATH/logic puzzle solutions.

    Sends a second fast LLM call that acts as a constraint checker:
    given the original problem and the proposed solution, it verifies
    every stated constraint and returns either VERIFIED or a list of
    violated constraints.

    Returns: (is_correct: bool, feedback: str)
    """
    verification_prompt = (
        f"TASK: Verify the following solution against ALL constraints in the problem.\n\n"
        f"ORIGINAL PROBLEM:\n{user_message}\n\n"
        f"PROPOSED SOLUTION:\n{solution}\n\n"
        "INSTRUCTIONS:\n"
        "1. Extract EVERY constraint from the original problem.\n"
        "2. Check EACH constraint against the proposed solution one by one.\n"
        "3. For each constraint write: OK or VIOLATED: <reason>.\n"
        "4. On the last line write either:\n"
        "   VERIFIED — if all constraints are satisfied, or\n"
        "   ERRORS FOUND: <count> — if any constraint is violated.\n"
        "Be systematic. Do not skip any constraint. Do not add assumptions."
    )

    verify_messages = [
        {"role": "system", "content": (
            "You are a strict logical constraint verifier. "
            "Your only job is to check whether a solution satisfies every stated constraint. "
            "Never suggest corrections — only verify. Be precise and systematic."
        )},
        {"role": "user", "content": verification_prompt},
    ]

    try:
        result = await fast_agent.run(verify_messages, temperature=temperature)
        if not result.success:
            return True, ""  # verification failed silently → pass through

        verdict = result.text.strip()
        last_line = verdict.split("\n")[-1].strip().upper()

        if last_line.startswith("VERIFIED"):
            return True, ""

        # Extract violation feedback for the correction round
        return False, verdict

    except Exception as exc:
        logger.warning("MATH verifier failed", extra={"error": str(exc)})
        return True, ""  # silent failure → pass through original solution


async def _correct_math_solution(
    messages: list[dict],
    original_solution: str,
    verification_feedback: str,
    temperature: float = 0.1,
) -> AgentResult:
    """
    Second-pass correction: give the agent its solution + verifier feedback,
    ask it to fix only the violated constraints.
    """
    correction_messages = list(messages) + [
        {"role": "assistant", "content": original_solution},
        {"role": "user", "content": (
            "Your solution above has constraint violations. "
            "The verifier found the following problems:\n\n"
            f"{verification_feedback}\n\n"
            "Fix ONLY the violated constraints. "
            "Re-check ALL constraints from the original problem after fixing. "
            "Show the corrected final answer table at the end."
        )},
    ]
    return await deep_agent.run(correction_messages, temperature=temperature)


def _agent_succeeded(result: AgentResult) -> bool:
    return result.success and bool(result.text.strip())


# ─── MAIN COORDINATOR ─────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
    reasoning_plan: str = "",
    temperature: float = 0.7,
    intent: Intent | None = None,
    lang: str = "en",
    tier: Tier = Tier.GENERAL,
) -> CoordinationResult:
    """
    Execute agent plan. Return CoordinationResult to orchestrator.

    Pipeline (ALLOW path):
      1. Primary agent
      2. Parallel validators (if any)
      3. safety_agent — LAST before Consensus (post-reasoning semantic validation)
      4. Consensus (ALLOW only, mutex with HEAVY)

    Pipeline (HEAVY_REQUIRED path):
      1. Primary agent (DEEP)
      2. safety_agent — mandatory
      3. Response Synthesizer aggregates directly (no Consensus)

    Pipeline (DEGRADED_MODE path):
      1. Fast agent only
      (safety_agent skipped on DEGRADED per architecture)

    GUARANTEE: blocked=False → text is always non-empty.
               blocked=True  → orchestrator renders deny message.
    """

    # ── primary agent ─────────────────────────────────────────────────────────
    primary_result = await _run_agent(plan.primary, messages, temperature)

    # ── consensus path (ALLOW only) ───────────────────────────────────────────
    if plan.use_consensus:
        if plan.parallel_validators:
            tasks = [
                _run_agent(vt, messages, temperature)
                for vt in plan.parallel_validators
            ]
            validator_results: list[AgentResult] = await asyncio.gather(*tasks)
        else:
            validator_results = []

        candidates = [
            r for r in [primary_result, *validator_results]
            if _agent_succeeded(r)
        ]

        # safety_agent: LAST before Consensus.
        # Candidate selection for safety check: first surviving candidate by position
        # (primary is always first in the list — [primary_result, *validator_results]).
        # Position-based selection is deterministic and unbiased: it does not favour
        # longer responses, does not defer to router authority, and preserves the
        # original plan ordering. If primary failed it is absent from candidates,
        # so we naturally fall to the next survivor. Fix audit §4.3.
        if candidates:
            safety_candidate = candidates[0]
            safety: SafetyResult = safety_check(SafetyInput(
                reasoning_plan=reasoning_plan,
                draft_response=safety_candidate.text,
                user_message=user_message,
            ))
            if safety.verdict == SafetyVerdict.BLOCK:
                logger.warning("safety_agent BLOCK before consensus",
                               extra={"reason": safety.reason})
                return CoordinationResult(
                    text="", model="", input_tokens=0, output_tokens=0,
                    blocked=True, block_reason="safety_block",
                )

        if candidates:
            consensus: ConsensusResult = await resolve(candidates)
            if consensus.text:
                return CoordinationResult(
                    text=consensus.text,
                    model=consensus.model,
                    input_tokens=consensus.input_tokens,
                    output_tokens=consensus.output_tokens,
                    actual_tier=candidates[0].actual_tier,
                )

        logger.warning("All consensus candidates failed — attempting fallback")

    # ── primary succeeded (non-consensus path) ────────────────────────────────
    if _agent_succeeded(primary_result):

        # ── MATH self-correction loop ─────────────────────────────────────────
        # For constraint-satisfaction and logic puzzles: verify the solution
        # against all stated constraints. If violations found → one correction
        # round. Max 1 correction to avoid infinite loops.
        if intent == Intent.MATH and user_message:
            is_correct, feedback = await _verify_math_solution(
                user_message=user_message,
                solution=primary_result.text,
                messages=messages,
                temperature=0.05,
            )
            if not is_correct and feedback:
                logger.info("MATH verifier found violations — attempting correction")
                corrected = await _correct_math_solution(
                    messages=messages,
                    original_solution=primary_result.text,
                    verification_feedback=feedback,
                    temperature=0.1,
                )
                if _agent_succeeded(corrected):
                    logger.info("MATH correction succeeded")
                    primary_result = corrected
                else:
                    logger.warning("MATH correction failed — using original solution")
            else:
                logger.info("MATH verifier passed")

        # HEAVY path: safety_agent mandatory
        # DEGRADED/EMOTIONAL/default-GENERAL: safety_agent skipped
        is_heavy = (tier == Tier.HEAVY)
        if is_heavy:
            safety = safety_check(SafetyInput(
                reasoning_plan=reasoning_plan,
                draft_response=primary_result.text,
                user_message=user_message,
            ))
            if safety.verdict == SafetyVerdict.BLOCK:
                logger.warning("safety_agent BLOCK on HEAVY path",
                               extra={"reason": safety.reason})
                return CoordinationResult(
                    text="", model="", input_tokens=0, output_tokens=0,
                    blocked=True, block_reason="safety_block",
                )

        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            input_tokens=primary_result.input_tokens,
            output_tokens=primary_result.output_tokens,
            actual_tier=primary_result.actual_tier,
        )

    # ── primary failed → fallback ─────────────────────────────────────────────
    logger.warning("Primary agent failed", extra={
        "agent": plan.primary,
        "error": getattr(primary_result, "error", ""),
    })

    if plan.fallback is not None and plan.fallback != plan.primary:
        logger.info("Trying fallback agent", extra={"agent": plan.fallback})
        fallback_result = await _run_agent(plan.fallback, messages, temperature)

        if _agent_succeeded(fallback_result):
            logger.info("Fallback agent succeeded")
            return CoordinationResult(
                text=fallback_result.text,
                model=fallback_result.model,
                input_tokens=fallback_result.input_tokens,
                output_tokens=fallback_result.output_tokens,
                actual_tier=fallback_result.actual_tier,
            )

        logger.error("Fallback agent also failed",
                     extra={"agent": plan.fallback})

    # ── all failed ────────────────────────────────────────────────────────────
    logger.error("All agents failed — returning blocked result")

    # Graceful fallback for EMOTIONAL intent: rule-based empathy response
    # avoids showing a cold error message when the user just vented.
    if intent == Intent.EMOTIONAL:
        fallback_text = _t("emotional_fallback", lang)
        logger.info("EMOTIONAL graceful fallback used", extra={"lang": lang})
        return CoordinationResult(
            text=fallback_text,
            model="rule-based-fallback",
            input_tokens=0,
            output_tokens=0,
        )

    return CoordinationResult(
        text="", model="", input_tokens=0, output_tokens=0,
        blocked=True, block_reason="no_response",
    )