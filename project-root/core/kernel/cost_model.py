from contracts.shared_types import Tier, Complexity

# ─── PRICING TABLES ─────────────────────────────────────────────────────────
# All rates in USD per 1M tokens

MODEL_RATES: dict[str, dict[str, float]] = {
    Tier.FAST:    {"input": 0.25,  "output": 0.9},
    Tier.GENERAL: {"input": 2.5,   "output": 10.0},
    Tier.HEAVY:   {"input": 8.0,   "output": 30.0},
}

EMBEDDING_RATES: dict[str, float] = {
    "large": 0.1,
    "small": 0.02,
}

RERANK_RATE: float = 1.0

# ─── OUTPUT ESTIMATION ───────────────────────────────────────────────────────

COMPLEXITY_MULTIPLIER: dict[str, float] = {
    Complexity.LOW:      1.2,
    Complexity.MEDIUM:   1.8,
    Complexity.HIGH:     2.5,
    Complexity.CRITICAL: 3.0,
}

MAX_OUTPUT_CAP: dict[str, int] = {
    Tier.FAST:    300,
    Tier.GENERAL: 1200,
    Tier.HEAVY:   3000,
}


def estimate_output_tokens(
    input_tokens: int,
    complexity: Complexity,
    tier: Tier,
) -> int:
    """
    Estimate output token count before execution.
    Used by EPK for pre-flight cost check.
    """
    raw = int(input_tokens * COMPLEXITY_MULTIPLIER[complexity])
    return min(raw, MAX_OUTPUT_CAP[tier])


# ─── COST ESTIMATION (PRE-EXECUTION) ────────────────────────────────────────

def estimate_cost(
    input_tokens: int,
    estimated_output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    """
    Estimated cost before LLM execution.
    Used by EPK to make ALLOW / DENY / DEGRADE decision.
    Returns USD.
    """
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + estimated_output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000


# ─── ACTUAL COST (POST-EXECUTION) ────────────────────────────────────────────

def actual_cost(
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    """
    Actual cost after LLM execution with real token counts.
    Used by usage_meter for billing and TON deduction.
    Returns USD.
    """
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000