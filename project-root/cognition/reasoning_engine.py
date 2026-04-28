from dataclasses import dataclass
from enum import Enum

from cognition.intent_engine import Intent
from contracts.shared_types import Tier


# ─── STRATEGY DEFINITIONS ────────────────────────────────────────────────────

class ReasoningMode(str, Enum):
    DIRECT          = "direct"          # answer immediately, no preamble
    CHAIN_OF_THOUGHT = "chain_of_thought"  # think step by step
    STRUCTURED      = "structured"      # use headers / numbered lists
    EXPLORATORY     = "exploratory"     # consider multiple angles


@dataclass(frozen=True)
class ReasoningStrategy:
    mode: ReasoningMode
    temperature: float          # passed to LLM
    instruction_prefix: str     # prepended to user message if non-empty
    max_reasoning_steps: int    # hint for agent layer


# ─── STRATEGY MATRIX ─────────────────────────────────────────────────────────
# (Intent, Tier) → ReasoningStrategy
# FAST tier always favours DIRECT to stay within token cap.

_STRATEGY_MATRIX: dict[tuple[str, str], ReasoningStrategy] = {

    # ── QUESTION ─────────────────────────────────────────
    (Intent.QUESTION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.QUESTION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.4,
        instruction_prefix="Think carefully, then answer:",
        max_reasoning_steps=3,
    ),
    (Intent.QUESTION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.3,
        instruction_prefix="Think carefully, then answer:",
        max_reasoning_steps=5,
    ),

    # ── CODE ─────────────────────────────────────────────
    (Intent.CODE, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CODE, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.2,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),
    (Intent.CODE, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.15,
        instruction_prefix="",
        max_reasoning_steps=5,
    ),

    # ── ANALYSIS ─────────────────────────────────────────
    (Intent.ANALYSIS, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.4,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.ANALYSIS, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.5,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=4,
    ),
    (Intent.ANALYSIS, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.4,
        instruction_prefix="Consider multiple perspectives:",
        max_reasoning_steps=6,
    ),

    # ── CREATIVE ─────────────────────────────────────────
    (Intent.CREATIVE, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.8,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CREATIVE, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.85,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.CREATIVE, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.EXPLORATORY,
        temperature=0.9,
        instruction_prefix="",
        max_reasoning_steps=3,
    ),

    # ── MATH ─────────────────────────────────────────────
    (Intent.MATH, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=3,
    ),
    (Intent.MATH, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.1,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=5,
    ),
    (Intent.MATH, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.CHAIN_OF_THOUGHT,
        temperature=0.05,
        instruction_prefix="Solve step by step:",
        max_reasoning_steps=8,
    ),

    # ── INSTRUCTION ──────────────────────────────────────
    (Intent.INSTRUCTION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.INSTRUCTION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.35,
        instruction_prefix="",
        max_reasoning_steps=4,
    ),
    (Intent.INSTRUCTION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.STRUCTURED,
        temperature=0.3,
        instruction_prefix="",
        max_reasoning_steps=6,
    ),

    # ── CONVERSATION ─────────────────────────────────────
    (Intent.CONVERSATION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CONVERSATION, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.CONVERSATION, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.7,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
}

_DEFAULT_STRATEGY = ReasoningStrategy(
    mode=ReasoningMode.DIRECT,
    temperature=0.5,
    instruction_prefix="",
    max_reasoning_steps=2,
)


def select_strategy(intent: Intent, tier: Tier) -> ReasoningStrategy:
    """
    Select reasoning strategy for a given intent + tier combination.
    Pure function. No I/O. No state.
    """
    return _STRATEGY_MATRIX.get((intent, tier), _DEFAULT_STRATEGY)