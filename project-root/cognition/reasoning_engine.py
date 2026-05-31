from dataclasses import dataclass
from enum import Enum

from contracts.shared_types import DomainHint, ReasoningDepth, RoutingProfile, Tier

# ─── STRATEGY DEFINITIONS ────────────────────────────────────────────────────

class ReasoningMode(str, Enum):
    DIRECT           = "direct"           # answer immediately, no preamble
    CHAIN_OF_THOUGHT = "chain_of_thought" # think step by step
    STRUCTURED       = "structured"       # use headers / numbered lists
    EXPLORATORY      = "exploratory"      # consider multiple angles


@dataclass(frozen=True)
class ReasoningStrategy:
    mode: ReasoningMode
    temperature: float          # passed to LLM
    instruction_prefix: str     # prepended to user message if non-empty
    max_reasoning_steps: int    # hint for agent layer


# ─── STRATEGY MATRIX ─────────────────────────────────────────────────────────
# (ReasoningDepth, DomainHint, Tier) → ReasoningStrategy
#
# Architecture contract (§7):
# - Reasoning engine consumes RoutingProfile axes, NOT Intent directly.
# - Intent is preserved in IntentResult for observability (logs, billing).
# - DomainHint selects the specialised pipeline (MATH CoT, CODE structured, etc.).
# - ReasoningDepth controls how much structured reasoning is applied.
# - Tier controls token budget and model capacity.
#
# Key invariants:
# - MATH CoT prefix fires ONLY when domain_hint == MATH.
#   MATH reasoning_depth == HEAVY ensures heavy CoT budget.
#   No other domain receives constraint-enumeration instructions.
# - FAST tier always favours DIRECT to stay within token cap.
# - NONE depth always resolves to DIRECT regardless of domain.

_STRATEGY_MATRIX: dict[tuple[str, str, str], ReasoningStrategy] = {

    # ── NONE depth — conversational, emotional, simple replies ────────────────
    # All NONE requests: always DIRECT, never CoT, warm temperature.
    (ReasoningDepth.NONE, DomainHint.GENERAL, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.NONE, DomainHint.GENERAL, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.NONE, DomainHint.GENERAL, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),

    # ── LIGHT depth, GENERAL domain — factual, search, instruction, analysis ──
    (ReasoningDepth.LIGHT, DomainHint.GENERAL, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix=(
            "Answer directly and concisely. "
            "If you don't know or aren't sure — say so in one sentence. "
            "Never list internal reasoning steps."
        ),
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.LIGHT, DomainHint.GENERAL, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.4,
        instruction_prefix=(
            "Answer directly. "
            "If you don't know — say so clearly and briefly. "
            "Do not simulate a search process or list candidates internally. "
            "Do not show reasoning steps — only the final answer."
        ),
        max_reasoning_steps=2,
    ),
    (ReasoningDepth.LIGHT, DomainHint.GENERAL, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix=(
            "Answer directly and accurately. "
            "If you are not confident — state your uncertainty explicitly. "
            "Do not list constraints, candidates, or verification steps. "
            "Show only the final answer, not the reasoning process."
        ),
        max_reasoning_steps=3,
    ),

    # ── LIGHT depth, GEO domain — search/maps/weather tool synthesis ──────────
    # compound_agent synthesises over retrieved tool output; no heavy CoT needed.
    (ReasoningDepth.LIGHT, DomainHint.GEO, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.LIGHT, DomainHint.GEO, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (ReasoningDepth.LIGHT, DomainHint.GEO, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),

    # ── LIGHT depth, CODE domain ──────────────────────────────────────────────
    (ReasoningDepth.LIGHT, DomainHint.CODE, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.LIGHT, DomainHint.CODE, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),
    (ReasoningDepth.LIGHT, DomainHint.CODE, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.15,
        instruction_prefix="",
        max_reasoning_steps=5,
    ),

    # ── LIGHT depth, MEDIA domain — creative exploration ──────────────────────
    (ReasoningDepth.LIGHT, DomainHint.MEDIA, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.8,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.LIGHT, DomainHint.MEDIA, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.85,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (ReasoningDepth.LIGHT, DomainHint.MEDIA, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.9,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),

    # ── HEAVY depth, MATH domain — constraint satisfaction + verification loop ─
    # instruction_prefix triggers the constraint-propagation protocol
    # defined in the MATH system prompt in intent_engine.py:
    # list all constraints → enumerate candidates → verify ALL simultaneously
    # → backtrack on contradiction → show verification table.
    # This prefix fires ONLY for domain_hint == MATH. No other domain receives it.
    (ReasoningDepth.HEAVY, DomainHint.MATH, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix=(
            "Before solving: list ALL constraints explicitly. "
            "Then enumerate candidates. "
            "Verify ALL constraints simultaneously for each candidate. "
            "Only then give the answer:"
        ),
        max_reasoning_steps=4,
    ),
    (ReasoningDepth.HEAVY, DomainHint.MATH, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix=(
            "Before solving: list ALL constraints explicitly. "
            "Then enumerate candidates systematically. "
            "For each candidate verify ALL constraints at once — not one by one. "
            "Backtrack fully if any constraint fails. "
            "Show a verification table for the final answer:"
        ),
        max_reasoning_steps=6,
    ),
    (ReasoningDepth.HEAVY, DomainHint.MATH, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.05,
        instruction_prefix=(
            "Before solving: list ALL constraints explicitly. "
            "Then enumerate ALL candidate solutions systematically. "
            "For each candidate verify ALL constraints simultaneously — never partially. "
            "A solution is valid only when every single constraint holds at the same time. "
            "Backtrack fully on any contradiction. "
            "Count truth-tellers/liars globally, not locally. "
            "Show the complete verification table for the final answer:"
        ),
        max_reasoning_steps=10,
    ),

    # ── HEAVY depth, GENERAL domain — exam, deep analysis ────────────────────
    (ReasoningDepth.HEAVY, DomainHint.GENERAL, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.1,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (ReasoningDepth.HEAVY, DomainHint.GENERAL, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.35,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=4,
    ),
    (ReasoningDepth.HEAVY, DomainHint.GENERAL, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.3,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=6,
    ),
}

_DEFAULT_STRATEGY = ReasoningStrategy(
    mode=ReasoningMode.DIRECT,
    temperature=0.5,
    instruction_prefix="",
    max_reasoning_steps=2,
)


def select_strategy(routing: RoutingProfile, tier: Tier) -> ReasoningStrategy:
    """
    Select reasoning strategy for a given RoutingProfile + Tier combination.
    Pure function. No I/O. No state.

    Lookup order: (depth, domain, tier) → exact match → (depth, GENERAL, tier)
    → default strategy. This ensures MEDIA/CODE/GEO domains always have coverage
    without requiring exhaustive cross-product entries for every depth × tier.
    """
    key = (routing.reasoning_depth, routing.domain_hint, tier)
    if key in _STRATEGY_MATRIX:
        return _STRATEGY_MATRIX[key]

    # Domain-agnostic fallback: try with GENERAL domain at same depth + tier
    general_key = (routing.reasoning_depth, DomainHint.GENERAL, tier)
    if general_key in _STRATEGY_MATRIX:
        return _STRATEGY_MATRIX[general_key]

    return _DEFAULT_STRATEGY