from __future__ import annotations

from contracts.shared_types import Tier

# ─── MODEL REGISTRY ───────────────────────────────────────────────────────────
# Source of truth for all model assignments per tier.
# Matches SSoT v6.3 exactly.

# Primary model per tier — used by default in all agent calls
_PRIMARY: dict[Tier, str] = {
    Tier.FAST:    "llama-3.1-8b-instant",
    Tier.GENERAL: "llama-3.3-70b-versatile",
    Tier.HEAVY:   "openai/gpt-oss-120b",
}

# All models available per tier (primary first)
_TIER_MODELS: dict[Tier, list[str]] = {
    Tier.FAST: [
        "llama-3.1-8b-instant",   # primary: lowest latency, 840 TPS
        # gemma2-9b-it removed — deprecated by Groq, August 2025
        # replacement: llama-3.1-8b-instant itself handles overflow via retry
    ],
    Tier.GENERAL: [
        "llama-3.3-70b-versatile",   # primary: reasoning + creative
        "qwen/qwen3-32b",            # structured logic / formatting (thinking: False enforced)
        "openai/gpt-oss-20b",        # constraint-aware general inference
    ],
    Tier.HEAVY: [
        "openai/gpt-oss-120b",               # primary: deep multi-step reasoning + consensus arbiter
        "llama-4-scout-17b-16e-instruct",    # long-context transformation (512K)
    ],
}

# Max output tokens per tier.
#
# These are hard limits passed directly to the Groq API.
# Set them high enough that responses are never cut mid-sentence,
# but not so high that latency and cost blow up on short queries.
#
# FAST:    1024  — conversation, emotional, fallback synthesis.
#                  800 was too tight: search fallback synthesis was truncating.
# GENERAL: 3072  — search synthesis, route queries, POI, code, analysis.
#                  2048 was cutting long search summaries and route descriptions.
# HEAVY:   6144  — deep reasoning, long documents, heavy consensus tasks.
#                  4096 was limiting for multi-source synthesis at HEAVY tier.
_MAX_TOKENS: dict[Tier, int] = {
    Tier.FAST:    1024,
    Tier.GENERAL: 3072,
    Tier.HEAVY:   6144,
}

# Special-purpose model assignments (not tiers — utility roles)
# heavy_input_shaper uses llama-3.1-8b-instant NOT as Fast Tier
SHAPER_MODEL    = "llama-3.1-8b-instant"

# Agent Layer (models.md §AGENT LAYER) — tool-use execution fabric.
# These are NOT tier models — they have tool selection authority.
# compound      → deep_agent.py  (multi-step, deep reasoning)
# compound-mini → fast_agent.py  (lightweight, single-step)
FAST_AGENT_MODEL = "groq/compound-mini"
DEEP_AGENT_MODEL = "groq/compound"

# Consensus arbiter — only active when Heavy Tier is NOT active (mutex)
CONSENSUS_MODEL = "openai/gpt-oss-120b"

# Multilingual normalization
MULTILINGUAL_ARABIC_MODEL = "allam-2-7b"
MULTILINGUAL_OTHER_MODEL  = "llama-3.3-70b-versatile"

# Long-context specialist (Heavy Tier secondary)
LONG_CONTEXT_MODEL = "llama-4-scout-17b-16e-instruct"

# qwen must always have thinking disabled
QWEN_THINKING_DISABLED_MODELS: frozenset[str] = frozenset({"qwen/qwen3-32b"})


# ─── PUBLIC API ───────────────────────────────────────────────────────────────

def route_model(tier: Tier) -> str:
    """Return the primary model for the given tier."""
    return _PRIMARY[tier]


def route_max_tokens(tier: Tier) -> int:
    """Return the max output tokens for the given tier."""
    return _MAX_TOKENS[tier]


def get_tier_models(tier: Tier) -> list[str]:
    """
    Return all models available for the given tier (primary first).
    Used by agents that need fallback within the same tier.
    """
    return list(_TIER_MODELS[tier])


def requires_thinking_disabled(model: str) -> bool:
    """
    Return True if the model must have thinking mode explicitly disabled.
    Applies to qwen/qwen3-32b — thinking: False must be enforced at call site.
    """
    return model in QWEN_THINKING_DISABLED_MODELS