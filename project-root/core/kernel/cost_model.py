from contracts.shared_types import Complexity, Tier

# ─── PRICING TABLES ──────────────────────────────────────────────────────────
# All rates in USD per 1M tokens — verified from Groq pricing page, May 2026.
#
# FAST    → llama-3.1-8b-instant:    $0.05 input / $0.08 output per 1M
# GENERAL → llama-3.3-70b-versatile: $0.59 input / $0.79 output per 1M
# HEAVY   → openai/gpt-oss-120b:     $0.15 input / $0.60 output per 1M
#
# Note: gpt-oss-120b is cheaper than 70B on output — MoE architecture.
# llama-4-scout (HEAVY secondary):   $0.11 input / $0.34 output per 1M

MODEL_RATES: dict[str, dict[str, float]] = {
    Tier.FAST:    {"input": 0.05,  "output": 0.08},
    Tier.GENERAL: {"input": 0.59,  "output": 0.79},
    Tier.HEAVY:   {"input": 0.15,  "output": 0.60},
}

# HuggingFace Inference API — BGE embeddings
# bge-large-en-v1.5: ~$0.10/1M tokens (HF serverless)
# bge-small-en-v1.5: ~$0.02/1M tokens
EMBEDDING_RATES: dict[str, float] = {
    "large": 0.10,
    "small": 0.02,
}

# BGE reranker-large — HF serverless, conservative estimate
RERANK_RATE: float = 0.10  # per 1M token-pairs (was 1.0 — 10x overestimate)

# ─── OUTPUT ESTIMATION ───────────────────────────────────────────────────────

COMPLEXITY_MULTIPLIER: dict[str, float] = {
    Complexity.LOW:      1.2,
    Complexity.MEDIUM:   1.8,
    Complexity.HIGH:     2.5,
    Complexity.CRITICAL: 3.0,
}

# Single source of truth — matches model_router._MAX_TOKENS exactly
MAX_OUTPUT_CAP: dict[str, int] = {
    Tier.FAST:    512,
    Tier.GENERAL: 2048,
    Tier.HEAVY:   4096,
}


def estimate_output_tokens(
    input_tokens: int,
    complexity: Complexity,
    tier: Tier,
) -> int:
    raw = int(input_tokens * COMPLEXITY_MULTIPLIER[complexity])
    return min(raw, MAX_OUTPUT_CAP[tier])


def estimate_cost(
    input_tokens: int,
    estimated_output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + estimated_output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000


def actual_cost(
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
) -> float:
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000