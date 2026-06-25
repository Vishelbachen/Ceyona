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

# Safety Layer rates — verified Groq pricing, Jun 2026. economic.md §1.2
# Both prompt-guard models are BERT classifiers: output is 1-2 tokens ("BENIGN"/"MALICIOUS").
# Output tokens negligible — billed at input rate for simplicity.
SAFETY_RATES: dict[str, dict[str, float]] = {
    "meta-llama/llama-prompt-guard-2-22m": {"input": 0.03,  "output": 0.03},   # $0.03/1M both
    "meta-llama/llama-prompt-guard-2-86m": {"input": 0.04,  "output": 0.04},   # $0.04/1M both
    "openai/gpt-oss-safeguard-20b":        {"input": 0.075, "output": 0.30},   # $0.075/$0.30 per 1M
}

# Conservative pre-execution token estimates for Safety Gate EPK input.
# Context window: 512 tokens for both prompt-guard models. Typical message: ~300 tokens.
# Actual tokens recorded post-execution in UsageEntry via actual_safety_cost().
_SAFETY_PASS1_ESTIMATED_TOKENS     = 300  # llama-prompt-guard-2-22m input
_SAFETY_PASS2_86M_ESTIMATED_TOKENS = 300  # llama-prompt-guard-2-86m input
_SAFETY_PASS2_SG_ESTIMATED_TOKENS  = 300  # gpt-oss-safeguard-20b input
_SAFETY_PASS2_SG_OUTPUT_ESTIMATED  = 2    # gpt-oss-safeguard-20b output ("SAFE"/"UNSAFE" ~2 tokens)


def estimate_safety_cost() -> float:
    """
    Pre-execution estimate of Safety Gate cost for EPK input (Variant C).

    Covers all three models called on every request (input + output):
      Pass 1: llama-prompt-guard-2-22m  (~300 input × $0.03/1M + ~2 output × $0.03/1M)
      Pass 2: llama-prompt-guard-2-86m  (~300 input × $0.04/1M + ~2 output × $0.04/1M)
      Pass 2: gpt-oss-safeguard-20b     (~300 input × $0.075/1M + ~2 output × $0.30/1M)

    Conservative input estimate (300 tokens). Output estimated at 2 tokens
    ("BENIGN"/"MALICIOUS" or "SAFE"/"UNSAFE"). Actual tokens recorded post-execution
    via actual_safety_cost(). economic.md §2: every call MUST be fully billed.

    Called by estimate_cost() — Safety Gate fires on every request, so its
    cost is a fixed overhead that EPK must account for.
    """
    sg = SAFETY_RATES["openai/gpt-oss-safeguard-20b"]
    r22 = SAFETY_RATES["meta-llama/llama-prompt-guard-2-22m"]
    r86 = SAFETY_RATES["meta-llama/llama-prompt-guard-2-86m"]
    pass1     = _SAFETY_PASS1_ESTIMATED_TOKENS     * r22["input"]  + 2 * r22["output"]
    pass2_86m = _SAFETY_PASS2_86M_ESTIMATED_TOKENS * r86["input"]  + 2 * r86["output"]
    pass2_sg  = _SAFETY_PASS2_SG_ESTIMATED_TOKENS  * sg["input"]   + _SAFETY_PASS2_SG_OUTPUT_ESTIMATED * sg["output"]
    return (pass1 + pass2_86m + pass2_sg) / 1_000_000


def actual_safety_cost(
    pass1_tokens: int,
    pass2_tokens: int,
    safeguard_tokens: int = 0,
    safeguard_output_tokens: int = 0,
) -> float:
    """
    Post-execution actual Safety Gate cost from real token counts (input + output).
    Recorded in UsageEntry after safety gate completes.
    Enables estimate vs actual drift tracking per request.
    economic.md §2: every model call MUST be fully billed — input AND output.
    """
    r22 = SAFETY_RATES["meta-llama/llama-prompt-guard-2-22m"]
    r86 = SAFETY_RATES["meta-llama/llama-prompt-guard-2-86m"]
    sg  = SAFETY_RATES["openai/gpt-oss-safeguard-20b"]
    return (
        pass1_tokens            * r22["input"]
        + pass2_tokens          * r86["input"]
        + safeguard_tokens      * sg["input"]
        + safeguard_output_tokens * sg["output"]
    ) / 1_000_000

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
    ) / 1_000_000 + estimate_safety_cost()


def actual_cost(
    input_tokens: int,
    output_tokens: int,
    embedding_tokens: int,
    rerank_tokens: int,
    tier: Tier,
    embedding_type: str = "large",
    safety_pass1_tokens: int = 0,
    safety_pass2_tokens: int = 0,
    safety_safeguard_tokens: int = 0,
    safety_safeguard_output_tokens: int = 0,  # gpt-oss-safeguard-20b output ($0.30/1M) — was missing
) -> float:
    rates = MODEL_RATES[tier]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + embedding_tokens * EMBEDDING_RATES[embedding_type]
        + rerank_tokens * RERANK_RATE
    ) / 1_000_000 + actual_safety_cost(
        pass1_tokens=safety_pass1_tokens,
        pass2_tokens=safety_pass2_tokens,
        safeguard_tokens=safety_safeguard_tokens,
        safeguard_output_tokens=safety_safeguard_output_tokens,
    )


# Multilingual model rates — economic.md §1.6
# allam-2-7b: no public pricing → treated as FAST equivalent ($0.075/$0.30 per 1M)
# qwen/qwen3.6-27b: GENERAL tier rates ($0.60/$3.00 per 1M)
# "passthrough": no LLM call — zero cost
_MULTILINGUAL_RATES: dict[str, dict[str, float]] = {
    "allam-2-7b":        {"input": 0.075, "output": 0.30},   # FAST equivalent (economic.md §1.6)
    "qwen/qwen3.6-27b":  {"input": 0.60,  "output": 3.00},   # GENERAL tier
    "passthrough":       {"input": 0.0,   "output": 0.0},    # no LLM call
}


def actual_multilingual_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """
    Compute actual billing cost for a multilingual_preprocessor LLM call.

    Called from webhook.py post-execution alongside actual_safety_cost().
    Model is carried from PreprocessorResult.model_used via OrchestratorResult.multilingual_model.

    Rates: allam-2-7b → FAST equivalent ($0.075/$0.30 per 1M, economic.md §1.6)
           qwen/qwen3.6-27b → GENERAL tier ($0.60/$3.00 per 1M, economic.md §1.1)
           passthrough → $0.00 (no LLM call)
    """
    if not input_tokens and not output_tokens:
        return 0.0
    rates = _MULTILINGUAL_RATES.get(model, _MULTILINGUAL_RATES["qwen/qwen3.6-27b"])
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000