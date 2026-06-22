from contracts.shared_types import Complexity, Tier

# ─── PRICING TABLES ──────────────────────────────────────────────────────────
# All rates in USD per 1M tokens — verified from Groq pricing page, Jun 2026.
#
# FAST    → openai/gpt-oss-20b:    $0.075 input / $0.30  output per 1M
# GENERAL → qwen/qwen3.6-27b:      $0.60  input / $3.00  output per 1M
# HEAVY   → openai/gpt-oss-120b:   $0.15  input / $0.60  output per 1M
#
# Note: gpt-oss-120b is cheaper than qwen3.6-27b on output — MoE architecture.
# Note: gpt-oss-120b (HEAVY) is cheaper than qwen3.6-27b (GENERAL) on output.
#       This is correct and expected — pricing follows architecture, not tier rank.
#
# Previous primary models (deprecated, removed):
#   FAST:    llama-3.1-8b-instant    $0.05/$0.08   — deprecated Aug 16, 2026
#   GENERAL: llama-3.3-70b-versatile $0.59/$0.79   — deprecated Aug 16, 2026

MODEL_RATES: dict[str, dict[str, float]] = {
    Tier.FAST:    {"input": 0.075, "output": 0.30},
    Tier.GENERAL: {"input": 0.60,  "output": 3.00},
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

# Conservative estimation caps — intentionally lower than model_router._MAX_TOKENS.
# These exist to make pre-execution cost estimates safe (never underestimate).
# model_router._MAX_TOKENS are the actual Groq API hard limits — different purpose.
#
# GENERAL cap set to 800 (was 2048) because qwen3.6-27b costs $3.00/output per 1M.
# At 2048 estimated output tokens: (1000×0.60 + 2048×3.00)/1M = $0.0068 → DEGRADED_MODE.
# At 800 estimated output tokens:  (1000×0.60 + 800×3.00)/1M  = $0.003  → ALLOW boundary.
# The 800-token cap is a conservative EPK estimation bound only — actual API limit
# remains 3072 (policy_registry.py). Requests with genuinely large output will
# naturally exceed the degrade_threshold and route accordingly.
MAX_OUTPUT_CAP: dict[str, int] = {
    Tier.FAST:    512,
    Tier.GENERAL: 800,   # lowered from 2048 — calibrated to $3.00/output (qwen3.6-27b)
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


def vision_actual_cost(input_tokens: int, output_tokens: int) -> float:
    """
    DEPRECATED — use payments.pricing_engine.vision_cost() instead.

    Kept for backward compatibility only. Forwards to the canonical
    implementation in payments/ where billing logic belongs.
    Removed the inline rates: source of truth is now _VISION_RATES
    in pricing_engine.py.
    """
    from payments.pricing_engine import vision_cost
    return vision_cost(input_tokens, output_tokens)