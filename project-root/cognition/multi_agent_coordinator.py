from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

import agents.compound_agent as compound_agent
import agents.creative_agent as creative_agent
import agents.deep_agent as deep_agent
import agents.fast_agent as fast_agent
from agents.fast_agent import AgentResult
from agents.safety_agent import SafetyInput, SafetyResult, SafetyVerdict
from agents.safety_agent import check_async as safety_check
from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from contracts.shared_types import DomainHint, ReasoningDepth, RoutingProfile, Tier
from i18n.t import t as _t

logger = logging.getLogger(__name__)


# ─── AGENT IDENTIFIERS ────────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST          = "fast"
    DEEP          = "deep"
    CREATIVE      = "creative"
    COMPOUND_FAST = "compound_fast"   # groq/compound-mini — tool-use, single-step
    COMPOUND_DEEP = "compound_deep"   # groq/compound     — tool-use, multi-step


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
class AgentCallMetrics:
    """
    Token accounting for all LLM calls inside coordinate().

    Three slots — primary, revision, safety — each tracks input+output tokens
    for one logical call type. Orchestrator unpacks these into flat fields on
    OrchestratorResult so the boundary toward webhook/usage_meter stays stable.

    revision slot: populated only when REVISE loop fires (max 1 pass).
    safety slot:   populated only on HEAVY path and consensus path.
    primary slot:  always populated (includes MATH extra tokens).

    economic.md §2: every model call MUST be billed — no zero-slot exceptions.
    """
    # primary agent tokens (includes MATH verify+correct extras, summed here)
    primary_input_tokens: int = 0
    primary_output_tokens: int = 0
    # revision pass tokens (SAFETY-6 REVISE loop — max 1 retry)
    revision_input_tokens: int = 0
    revision_output_tokens: int = 0
    # safety_agent LLM judge tokens (gpt-oss-safeguard-20b)
    safety_input_tokens: int = 0
    safety_output_tokens: int = 0


@dataclass
class CoordinationResult:
    text: str
    model: str
    blocked: bool = False
    block_reason: str = ""
    actual_tier: str = ""  # tier that actually executed (may be lower than requested on cascade)
    tool_calls: int = 0   # total compound tool calls executed — flows to billing
    metrics: AgentCallMetrics = field(default_factory=AgentCallMetrics)
    # Per-model token breakdown from compound AI system — flows to OrchestratorResult.compound_breakdown.
    usage_breakdown: list = field(default_factory=list)

    # ── convenience properties — orchestrator reads these, not metrics directly ──
    @property
    def input_tokens(self) -> int:
        return self.metrics.primary_input_tokens

    @property
    def output_tokens(self) -> int:
        return self.metrics.primary_output_tokens

    @property
    def safety_agent_input_tokens(self) -> int:
        return self.metrics.safety_input_tokens

    @property
    def safety_agent_output_tokens(self) -> int:
        return self.metrics.safety_output_tokens

    @property
    def revision_input_tokens(self) -> int:
        return self.metrics.revision_input_tokens

    @property
    def revision_output_tokens(self) -> int:
        return self.metrics.revision_output_tokens


# ─── PLAN SELECTION ───────────────────────────────────────────────────────────

def plan_agents(
    routing: RoutingProfile,
    tier: Tier,
    strategy: ReasoningStrategy,
    intent: Intent | None = None,
) -> AgentPlan:
    """
    Select agent plan based on RoutingProfile + Tier + ReasoningStrategy.
    Pure function. No I/O. No state. No LLM calls. NO policy authority.

    Architecture contract (§16):
    - routing.domain_hint drives the specialised pipeline selection.
    - routing.reasoning_depth informs depth of execution.
    - intent is retained as an optional observability hint only —
      it does NOT make routing decisions here.

    HEAVY_REQUIRED tier:
      primary=DEEP, no consensus (mutex), no Fast validators.
    ALLOW tier:
      Fast → General → Agents → safety_agent → Consensus.
    DEGRADED_MODE:
      Fast only (orchestrator routes here directly, plan is minimal).
    """
    # HEAVY_REQUIRED — consensus is skipped (mutex with Heavy Tier, §22)
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

    # ── ALLOW — GENERAL tier ──────────────────────────────────────────────────

    # MEDIA domain: exploratory — creative + consensus for quality
    if routing.domain_hint == DomainHint.MEDIA:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    # EXPLORATORY mode (analysis, some HEAVY.GENERAL): deep + consensus
    if strategy.mode == ReasoningMode.EXPLORATORY:
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=True,
            parallel_validators=[AgentType.FAST],
            temperature=strategy.temperature,
        )

    # GEO domain: all data-driven intents — compound owns tool execution + reasoning.
    # Architecture decision (май 2026): ALL tool intents go through compound.
    # compound-mini (fast) for FAST tier, compound (deep) for GENERAL.
    # Fallback: DEEP agent (openai/gpt-oss-120b) — plain-text, always available.
    if routing.domain_hint == DomainHint.GEO:
        primary = AgentType.COMPOUND_FAST if tier == Tier.FAST else AgentType.COMPOUND_DEEP
        return AgentPlan(
            primary=primary,
            fallback=AgentType.DEEP,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # MATH, CODE, GENERAL with LIGHT/HEAVY depth: single deep agent, no consensus
    if routing.reasoning_depth in (ReasoningDepth.LIGHT, ReasoningDepth.HEAVY):
        return AgentPlan(
            primary=AgentType.DEEP,
            fallback=AgentType.FAST,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # NONE depth (conversation, emotional): fast agent, warm temperature
    if routing.reasoning_depth == ReasoningDepth.NONE:
        return AgentPlan(
            primary=AgentType.FAST,
            fallback=None,
            use_consensus=False,
            parallel_validators=[],
            temperature=strategy.temperature,
        )

    # default GENERAL fallback
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
    lang: str = "en",
    tier: Tier = Tier.GENERAL,
) -> AgentResult:
    """
    Dispatch to the correct agent module based on AgentType.
    Returns AgentResult. Never raises — catches all exceptions and returns
    a failed AgentResult so the coordinator can handle fallback/blocking.
    """
    try:
        if agent_type == AgentType.COMPOUND_DEEP:
            return await compound_agent.run_deep(messages=messages, lang=lang, temperature=temperature, tier=tier)
        if agent_type == AgentType.COMPOUND_FAST:
            return await compound_agent.run_fast(messages=messages, lang=lang, temperature=temperature)
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


# ─── MATH VERIFICATION (domain_hint == MATH) ──────────────────────────────────

async def _verify_math_solution(
    user_message: str,
    solution: str,
    messages: list[dict],
    temperature: float = 0.1,
) -> tuple[bool, str, int, int]:
    """
    Self-verification step for MATH/logic puzzle solutions.

    Sends a second fast LLM call that acts as a constraint checker:
    given the original problem and the proposed solution, it verifies
    every stated constraint and returns either VERIFIED or a list of
    violated constraints.

    Returns: (is_correct: bool, feedback: str, input_tokens: int, output_tokens: int)
    BUG-O3 fix: token counts added so the caller can accumulate them for billing.
    economic.md §2: every model call MUST be billed — including this verifier call.
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
            return True, "", result.input_tokens, result.output_tokens

        verdict = result.text.strip()
        last_line = verdict.split("\n")[-1].strip().upper()

        if last_line.startswith("VERIFIED"):
            return True, "", result.input_tokens, result.output_tokens

        # Extract violation feedback for the correction round
        return False, verdict, result.input_tokens, result.output_tokens

    except Exception as exc:
        logger.warning("MATH verifier failed", extra={"error": str(exc)})
        return True, "", 0, 0  # silent failure → pass through original solution


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


def _build_revision_messages(
    messages: list[dict],
    draft: str,
    reason: str,
) -> list[dict]:
    """
    Construct messages for the REVISE retry pass.

    Appends the draft as an assistant turn + a user revision instruction
    carrying SafetyResult.reason so the model knows exactly what to fix.

    Tool outputs and prior context are preserved — the revision is a
    targeted rewrite, not a new pipeline. reasoning_plan is NOT re-run
    (§21: revision = correction pass, not new reasoning).

    architecture.md §21 / SAFETY-6.
    """
    revision_instruction = (
        "Revision required.\n\n"
        f"Reason:\n{reason}\n\n"
        "Rewrite the answer while preserving all useful information "
        "and removing the unsafe or problematic content identified above."
    )
    return list(messages) + [
        {"role": "assistant", "content": draft},
        {"role": "user",      "content": revision_instruction},
    ]


# ─── MAIN COORDINATOR ─────────────────────────────────────────────────────────

async def coordinate(
    plan: AgentPlan,
    messages: list[dict],
    user_message: str,
    routing: RoutingProfile,
    reasoning_plan: str = "",
    temperature: float = 0.7,
    intent: Intent | None = None,
    lang: str = "en",
    tier: Tier = Tier.GENERAL,
) -> CoordinationResult:
    """
    Execute agent plan. Return CoordinationResult to orchestrator.

    Architecture contract (§16):
    - routing.domain_hint == MATH activates the verification loop (not intent).
    - intent is retained for EMOTIONAL graceful fallback (rule-based, no LLM).
    - All other policy decisions come from routing, not intent.

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
      (safety_agent skipped on DEGRADED per architecture §21)

    GUARANTEE: blocked=False → text is always non-empty.
               blocked=True  → orchestrator renders deny message.
    """

    # ── primary agent ─────────────────────────────────────────────────────────
    primary_result = await _run_agent(plan.primary, messages, temperature, lang=lang, tier=tier)

    # ── consensus path (ALLOW only) ───────────────────────────────────────────
    if plan.use_consensus:
        if plan.parallel_validators:
            tasks = [
                _run_agent(vt, messages, temperature, lang=lang, tier=tier)
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
        # Position-based selection is deterministic — primary is always first.
        # _safety_result initialised to None — explicit pattern, no locals() (§21 rule 4).
        _safety_result: SafetyResult | None = None
        if candidates:
            safety_candidate = candidates[0]
            _safety_result = await safety_check(SafetyInput(
                reasoning_plan=reasoning_plan,
                draft_response=safety_candidate.text,
                user_message=user_message,
            ))
            if _safety_result.verdict == SafetyVerdict.BLOCK:
                logger.warning("safety_agent BLOCK before consensus",
                               extra={"reason": _safety_result.reason})
                return CoordinationResult(
                    text="", model="", blocked=True, block_reason="safety_block",
                    metrics=AgentCallMetrics(
                        primary_input_tokens=primary_result.input_tokens,
                        primary_output_tokens=primary_result.output_tokens,
                        safety_input_tokens=_safety_result.input_tokens,
                        safety_output_tokens=_safety_result.output_tokens,
                    ),
                )

            # ── REVISE loop — HEAVY path (SAFETY-6) ──────────────────────────
            # Max 1 retry. reasoning_plan not re-run — revision pass only.
            # If second pass returns REVISE again → pass-through (audit.md §SAFETY-6).
            if _sa_result.verdict == SafetyVerdict.REVISE:
                logger.info("safety_agent REVISE on HEAVY path — attempting revision pass")
                _rev_messages = _build_revision_messages(
                    messages=messages,
                    draft=primary_result.text,
                    reason=_sa_result.reason,
                )
                _rev_result = await _run_agent(
                    plan.primary, _rev_messages, temperature, lang=lang, tier=tier,
                )
                _rev_in  = _rev_result.input_tokens
                _rev_out = _rev_result.output_tokens
                if _agent_succeeded(_rev_result):
                    logger.info("Revision pass succeeded on HEAVY path")
                    primary_result = _rev_result
                else:
                    logger.warning("Revision pass failed on HEAVY path — using original draft")

            if _sa_result.verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
                # Judge unavailable — fail-open with full observability (§21 contract).
                logger.warning("safety_agent UNAVAILABLE on HEAVY path — proceeding fail-open")

        # BUG-O4 fix: explicit _sa_result variable — locals() / is_heavy bool forbidden (§21 rule 4).
        _sa_in  = _sa_result.input_tokens  if _sa_result is not None else 0
        _sa_out = _sa_result.output_tokens if _sa_result is not None else 0
        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            actual_tier=primary_result.actual_tier,
            tool_calls=getattr(primary_result, "tool_calls", 0),
            metrics=AgentCallMetrics(
                primary_input_tokens=primary_result.input_tokens + _math_extra_in,
                primary_output_tokens=primary_result.output_tokens + _math_extra_out,
                revision_input_tokens=_rev_in,
                revision_output_tokens=_rev_out,
                safety_input_tokens=_sa_in,
                safety_output_tokens=_sa_out,
            ),
            usage_breakdown=getattr(primary_result, "usage_breakdown", []),
        )

    # ── primary failed → fallback ─────────────────────────────────────────────
    logger.warning("Primary agent failed", extra={
        "agent": plan.primary,
        "error": getattr(primary_result, "error", ""),
    })
    # BUG-O5 fix: primary agent made a real Groq API call before failing.
    # economic.md §2: "Failed calls that returned no output" are not billed —
    # but only for genuine API/network errors (no tokens consumed).
    # If primary returned a response but it was empty/malformed, tokens were
    # consumed. We add primary tokens to fallback result to avoid silent loss.
    # If primary failed with a network error, its input_tokens = 0 (safe to add).
    _failed_primary_in  = primary_result.input_tokens
    _failed_primary_out = primary_result.output_tokens

    if plan.fallback is not None and plan.fallback != plan.primary:
        logger.info("Trying fallback agent", extra={"agent": plan.fallback})
        fallback_result = await _run_agent(plan.fallback, messages, temperature, lang=lang, tier=tier)

        if _agent_succeeded(fallback_result):
            logger.info("Fallback agent succeeded")
            return CoordinationResult(
                text=fallback_result.text,
                model=fallback_result.model,
                actual_tier=fallback_result.actual_tier,
                tool_calls=getattr(fallback_result, "tool_calls", 0),
                metrics=AgentCallMetrics(
                    # primary tokens included per BUG-O5 — may be 0 on network error
                    primary_input_tokens=fallback_result.input_tokens + _failed_primary_in,
                    primary_output_tokens=fallback_result.output_tokens + _failed_primary_out,
                ),
                usage_breakdown=getattr(fallback_result, "usage_breakdown", []),
            )

        logger.error("Fallback agent also failed",
                     extra={"agent": plan.fallback})

    # ── all failed ────────────────────────────────────────────────────────────
    logger.error("All agents failed — returning blocked result")

    # Graceful fallback for EMOTIONAL intent: rule-based empathy response.
    # Intent is the correct signal here — not routing — because EMOTIONAL
    # is an affective state, not a capability requirement. The rule-based
    # fallback avoids showing a cold error when the user just vented.
    if intent == Intent.EMOTIONAL:
        fallback_text = _t("emotional_fallback", lang)
        logger.info("EMOTIONAL graceful fallback used", extra={"lang": lang})
        return CoordinationResult(
            text=fallback_text,
            model="rule-based-fallback",
            metrics=AgentCallMetrics(),
        )

    return CoordinationResult(
        text="", model="", blocked=True, block_reason="no_response",
        metrics=AgentCallMetrics(),
    )