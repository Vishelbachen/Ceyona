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
    # instruction_prefix must NOT trigger constraint-listing or candidate-matching
    # CoT patterns — those leak into user-facing output (audit §13.3).
    # Graceful exit rule is mandatory: if you don't know, say so directly.
    # Never simulate a search loop or list internal reasoning steps.
    (Intent.QUESTION, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.3,
        instruction_prefix=(
            "Answer directly and concisely. "
            "If you don't know or aren't sure — say so in one sentence. "
            "Never list internal reasoning steps."
        ),
        max_reasoning_steps=1,
    ),
    (Intent.QUESTION, Tier.GENERAL): ReasoningStrategy(
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
    (Intent.QUESTION, Tier.HEAVY): ReasoningStrategy(
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
    # instruction_prefix triggers the constraint-propagation protocol
    # defined in the MATH system prompt in intent_engine.py:
    # list all constraints → enumerate candidates → verify ALL simultaneously
    # → backtrack on contradiction → show verification table.
    (Intent.MATH, Tier.FAST): ReasoningStrategy(
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
    (Intent.MATH, Tier.GENERAL): ReasoningStrategy(
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
    (Intent.MATH, Tier.HEAVY): ReasoningStrategy(
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

    # ── EXAM ──────────────────────────────────────────────
    (Intent.EXAM, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.1,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.EXAM, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.1,
        instruction_prefix="",
        max_reasoning_steps=2,
    ),
    (Intent.EXAM, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.1,
        instruction_prefix="",
        max_reasoning_steps=2,
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

    # ── EMOTIONAL ────────────────────────────────────────────
    # Short empathetic reaction — always DIRECT, warm temperature,
    # no instruction prefix (the system prompt already handles framing),
    # single step (no chain-of-thought needed for a 1–3 sentence reply).
    (Intent.EMOTIONAL, Tier.FAST): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.85,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.EMOTIONAL, Tier.GENERAL): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.85,
        instruction_prefix="",
        max_reasoning_steps=1,
    ),
    (Intent.EMOTIONAL, Tier.HEAVY): ReasoningStrategy(
        mode=ReasoningMode.DIRECT,
        temperature=0.85,
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