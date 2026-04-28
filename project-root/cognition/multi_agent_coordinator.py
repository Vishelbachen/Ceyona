from dataclasses import dataclass, field
from enum import Enum

from cognition.intent_engine import Intent
from cognition.reasoning_engine import ReasoningMode, ReasoningStrategy
from contracts.shared_types import Tier


# ─── AGENT IDENTIFIERS ───────────────────────────────────────────────────────

class AgentType(str, Enum):
    FAST      = "fast_agent"
    DEEP      = "deep_agent"
    CREATIVE  = "creative_agent"
    SAFETY    = "safety_agent"


# ─── AGENT PLAN ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentPlan:
    primary: AgentType
    validators: list[AgentType] = field(default_factory=list)
    use_consensus: bool = False
    parallel: bool = False          # run validators in parallel if True


# ─── COORDINATION LOGIC ──────────────────────────────────────────────────────

def plan_agents(
    intent: Intent,
    tier: Tier,
    strategy: ReasoningStrategy,
) -> AgentPlan:
    """
    Select which agents to activate.
    Pure function. No I/O. No state. No LLM calls.

    Rules:
    - FAST tier → fast_agent only (cost constraint)
    - HEAVY tier → deep_agent + safety validation + consensus
    - Creative intent → creative_agent primary
    - EXPLORATORY mode → parallel validation
    """

    # ── FAST tier: single agent, no overhead ────────────
    if tier == Tier.FAST:
        return AgentPlan(
            primary=AgentType.FAST,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=False,
        )

    # ── Creative intent: creative_agent primary ──────────
    if intent == Intent.CREATIVE:
        return AgentPlan(
            primary=AgentType.CREATIVE,
            validators=[AgentType.SAFETY],
            use_consensus=False,
            parallel=True,
        )

    # ── HEAVY tier: deep reasoning + full validation ─────
    if tier == Tier.HEAVY:
        return AgentPlan(
            primary=AgentType.DEEP,
            validators=[AgentType.FAST, AgentType.SAFETY],
            use_consensus=True,
            parallel=True,
        )

    # ── GENERAL tier: intent-driven selection ────────────
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

    # ── default GENERAL ──────────────────────────────────
    return AgentPlan(
        primary=AgentType.FAST,
        validators=[AgentType.SAFETY],
        use_consensus=False,
        parallel=False,
    )