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
from events.event_bus import event_bus
from events.event_types import SafetyBlockEvent
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

@dataclass(frozen=True)
class AgentCallMetrics:
    """
    Universal token contract for any single LLM call inside the orchestrator.

    Rule (ChatGPT / architecture decision):
      Any component that has its own prompt + its own completion is an agent.
      Agents live inside orchestrator. AgentCallMetrics is their billing contract.
      No exceptions: multilingual, reflection, safety, correction, analysis,
      summarizer, planner — all qualify if they make an independent LLM call.

    frozen=True: immutable after creation. Transport layer MUST NOT mutate
    OrchestratorResult to add tokens post-facto — that is an architectural
    violation (orchestrator must return a fully populated result).

    economic.md §2: every model call MUST be billed — no zero-slot exceptions.
    """
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    retries: int = 0


@dataclass(frozen=True)
class CoordinationMetrics:
    """
    Aggregates AgentCallMetrics for all LLM-agents in the pipeline.

    Slots use dict[str, AgentCallMetrics] for maximum extensibility —
    adding a new agent (Planner, Critic, Summarizer) requires zero
    changes to this dataclass. Orchestrator unpacks into flat fields
    on OrchestratorResult for billing/webhook stability.

    Naming convention for well-known slots:
      primary      — main reasoning agent (fast/deep/creative/compound)
      consensus    — gpt-oss-120b consensus arbitration
      safety       — safety_agent LLM judge (gpt-oss-safeguard-20b)
      revision     — SAFETY-6 REVISE loop (max 1 retry, primary model)
      reflection   — meta/reflection async side-channel
      multilingual — multilingual_preprocessor LLM call (allam-2-7b | qwen3.6-27b)
      lc_transformer — long_context_transformer (qwen3.6-27b, HEAVY pre-shaper)
    """
    agents: dict = None  # dict[str, AgentCallMetrics]

    def __post_init__(self):
        # frozen=True requires object.__setattr__ for post-init defaults
        if self.agents is None:
            object.__setattr__(self, "agents", {})

    def get(self, name: str) -> AgentCallMetrics:
        """Return metrics for a named agent slot, or empty metrics if absent."""
        return self.agents.get(name, AgentCallMetrics())

    @property
    def primary(self) -> AgentCallMetrics:
        return self.get("primary")

    @property
    def safety(self) -> AgentCallMetrics:
        return self.get("safety")

    @property
    def revision(self) -> AgentCallMetrics:
        return self.get("revision")

    @property
    def multilingual(self) -> AgentCallMetrics:
        return self.get("multilingual")

    @property
    def lc_transformer(self) -> AgentCallMetrics:
        return self.get("lc_transformer")

    # ── convenience: sum all input/output tokens across all agents ──────────
    @property
    def total_input_tokens(self) -> int:
        return sum(m.input_tokens for m in self.agents.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(m.output_tokens for m in self.agents.values())

    def with_agent(self, name: str, metrics: AgentCallMetrics) -> "CoordinationMetrics":
        """Return a new CoordinationMetrics with the named agent slot set."""
        new_agents = dict(self.agents)
        new_agents[name] = metrics
        return CoordinationMetrics(agents=new_agents)


def _make_agent_metrics(
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: int = 0,
    retries: int = 0,
) -> AgentCallMetrics:
    """Helper: construct AgentCallMetrics from raw token counts."""
    return AgentCallMetrics(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        retries=retries,
    )


@dataclass
class CoordinationResult:
    text: str
    model: str
    blocked: bool = False
    block_reason: str = ""
    actual_tier: str = ""
    tool_calls: int = 0
    coordination_metrics: CoordinationMetrics = field(default_factory=CoordinationMetrics)
    usage_breakdown: list = field(default_factory=list)

    # ── convenience properties ─────────────────────────────────────────────────
    @property
    def input_tokens(self) -> int:
        return self.coordination_metrics.primary.input_tokens

    @property
    def output_tokens(self) -> int:
        return self.coordination_metrics.primary.output_tokens

    @property
    def safety_agent_input_tokens(self) -> int:
        return self.coordination_metrics.safety.input_tokens

    @property
    def safety_agent_output_tokens(self) -> int:
        return self.coordination_metrics.safety.output_tokens

    @property
    def revision_input_tokens(self) -> int:
        return self.coordination_metrics.revision.input_tokens

    @property
    def revision_output_tokens(self) -> int:
        return self.coordination_metrics.revision.output_tokens

    @property
    def multilingual_input_tokens(self) -> int:
        return self.coordination_metrics.multilingual.input_tokens

    @property
    def multilingual_output_tokens(self) -> int:
        return self.coordination_metrics.multilingual.output_tokens

    @property
    def multilingual_model(self) -> str:
        return self.coordination_metrics.multilingual.model

    @property
    def lc_transformer_input_tokens(self) -> int:
        return self.coordination_metrics.lc_transformer.input_tokens

    @property
    def lc_transformer_output_tokens(self) -> int:
        return self.coordination_metrics.lc_transformer.output_tokens


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
                # Publish safety.block event — triggers event_notifier.on_safety_block()
                # user_id not available in coordinator — webhook will add it via context.
                # Non-blocking: wrapped in asyncio.create_task() by event_bus.
                try:
                    await event_bus.publish(SafetyBlockEvent(
                        user_id=None,   # enriched by update_handler via CoordinationResult.block_reason
                        payload={
                            "reason": _safety_result.reason or "safety_block",
                            "tier": tier.value if tier else "",
                        },
                    ))
                except Exception as _pub_exc:
                    logger.warning("SafetyBlockEvent publish failed", extra={"error": str(_pub_exc)})
                return CoordinationResult(
                    text="", model="", blocked=True, block_reason="safety_block",
                    coordination_metrics=CoordinationMetrics(agents={
                        "primary": _make_agent_metrics(
                            model=getattr(primary_result, "model", ""),
                            input_tokens=primary_result.input_tokens,
                            output_tokens=primary_result.output_tokens,
                        ),
                        "safety": _make_agent_metrics(
                            model="openai/gpt-oss-safeguard-20b",
                            input_tokens=_safety_result.input_tokens,
                            output_tokens=_safety_result.output_tokens,
                        ),
                    }),
                )

            # ── REVISE loop (SAFETY-6) ───────────────────────────────────────
            # Max 1 retry. Fix: was referencing _sa_result (undefined) — use _safety_result.
            _rev_in  = 0
            _rev_out = 0
            if _safety_result is not None and _safety_result.verdict == SafetyVerdict.REVISE:
                logger.info("safety_agent REVISE on consensus path — attempting revision pass")
                _rev_messages = _build_revision_messages(
                    messages=messages,
                    draft=primary_result.text,
                    reason=_safety_result.reason,
                )
                _rev_result = await _run_agent(
                    plan.primary, _rev_messages, temperature, lang=lang, tier=tier,
                )
                _rev_in  = _rev_result.input_tokens
                _rev_out = _rev_result.output_tokens
                if _agent_succeeded(_rev_result):
                    logger.info("Revision pass succeeded on consensus path")
                    primary_result = _rev_result
                else:
                    logger.warning("Revision pass failed — using original draft")

            if _safety_result is not None and _safety_result.verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
                logger.warning("safety_agent UNAVAILABLE on consensus path — proceeding fail-open")

        _sa_in  = _safety_result.input_tokens  if _safety_result is not None else 0
        _sa_out = _safety_result.output_tokens if _safety_result is not None else 0
        _math_extra_in  = 0
        _math_extra_out = 0
        _agents_dict: dict = {
            "primary": _make_agent_metrics(
                model=primary_result.model,
                input_tokens=primary_result.input_tokens + _math_extra_in,
                output_tokens=primary_result.output_tokens + _math_extra_out,
            ),
        }
        if _sa_in or _sa_out:
            _agents_dict["safety"] = _make_agent_metrics(
                model="openai/gpt-oss-safeguard-20b",
                input_tokens=_sa_in,
                output_tokens=_sa_out,
            )
        if _rev_in or _rev_out:
            _agents_dict["revision"] = _make_agent_metrics(
                model=primary_result.model,
                input_tokens=_rev_in,
                output_tokens=_rev_out,
            )
        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            actual_tier=primary_result.actual_tier,
            tool_calls=getattr(primary_result, "tool_calls", 0),
            coordination_metrics=CoordinationMetrics(agents=_agents_dict),
            usage_breakdown=getattr(primary_result, "usage_breakdown", []),
        )

    # ── non-consensus path (HEAVY or simple ALLOW without validators) ────────
    # safety_agent runs here — architecture §21: every path has post-check.
    if not plan.use_consensus and _agent_succeeded(primary_result):
        _sa_result_nc: SafetyResult | None = None
        _rev_in_nc  = 0
        _rev_out_nc = 0

        _sa_result_nc = await safety_check(SafetyInput(
            reasoning_plan=reasoning_plan,
            draft_response=primary_result.text,
            user_message=user_message,
        ))

        if _sa_result_nc.verdict == SafetyVerdict.BLOCK:
            logger.warning("safety_agent BLOCK on non-consensus path",
                           extra={"reason": _sa_result_nc.reason})
            try:
                await event_bus.publish(SafetyBlockEvent(
                    user_id=None,
                    payload={"reason": _sa_result_nc.reason or "safety_block", "tier": tier.value if tier else ""},
                ))
            except Exception as _pub_exc:
                logger.warning("SafetyBlockEvent publish failed", extra={"error": str(_pub_exc)})
            return CoordinationResult(
                text="", model="", blocked=True, block_reason="safety_block",
                coordination_metrics=CoordinationMetrics(agents={
                    "primary": _make_agent_metrics(model=primary_result.model, input_tokens=primary_result.input_tokens, output_tokens=primary_result.output_tokens),
                    "safety": _make_agent_metrics(model="openai/gpt-oss-safeguard-20b", input_tokens=_sa_result_nc.input_tokens, output_tokens=_sa_result_nc.output_tokens),
                }),
            )

        if _sa_result_nc.verdict == SafetyVerdict.REVISE:
            logger.info("safety_agent REVISE on non-consensus — revision pass")
            _rev_r = await _run_agent(
                plan.primary,
                _build_revision_messages(messages=messages, draft=primary_result.text, reason=_sa_result_nc.reason),
                temperature, lang=lang, tier=tier,
            )
            _rev_in_nc  = _rev_r.input_tokens
            _rev_out_nc = _rev_r.output_tokens
            if _agent_succeeded(_rev_r):
                primary_result = _rev_r

        if _sa_result_nc.verdict == SafetyVerdict.SAFETY_UNAVAILABLE:
            logger.warning("safety_agent UNAVAILABLE on non-consensus — fail-open")

        _nc_sa_in  = _sa_result_nc.input_tokens  if _sa_result_nc else 0
        _nc_sa_out = _sa_result_nc.output_tokens if _sa_result_nc else 0
        _nc_agents: dict = {
            "primary": _make_agent_metrics(model=primary_result.model, input_tokens=primary_result.input_tokens, output_tokens=primary_result.output_tokens),
        }
        if _nc_sa_in or _nc_sa_out:
            _nc_agents["safety"] = _make_agent_metrics(model="openai/gpt-oss-safeguard-20b", input_tokens=_nc_sa_in, output_tokens=_nc_sa_out)
        if _rev_in_nc or _rev_out_nc:
            _nc_agents["revision"] = _make_agent_metrics(model=primary_result.model, input_tokens=_rev_in_nc, output_tokens=_rev_out_nc)
        return CoordinationResult(
            text=primary_result.text,
            model=primary_result.model,
            actual_tier=getattr(primary_result, "actual_tier", ""),
            tool_calls=getattr(primary_result, "tool_calls", 0),
            coordination_metrics=CoordinationMetrics(agents=_nc_agents),
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
                coordination_metrics=CoordinationMetrics(agents={
                    "primary": _make_agent_metrics(
                        model=fallback_result.model,
                        # BUG-O5: include failed primary tokens
                        input_tokens=fallback_result.input_tokens + _failed_primary_in,
                        output_tokens=fallback_result.output_tokens + _failed_primary_out,
                    ),
                }),
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
            coordination_metrics=CoordinationMetrics(),
        )

    return CoordinationResult(
        text="", model="", blocked=True, block_reason="no_response",
        coordination_metrics=CoordinationMetrics(),
    )