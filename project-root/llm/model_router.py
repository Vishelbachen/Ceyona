from __future__ import annotations

from contracts.shared_types import Tier
from core.kernel.policy_registry import RUNTIME

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
        "meta-llama/llama-4-scout-17b-16e-instruct",  # long-context transformation (512K)
    ],
}

# Max output tokens per tier — read from policy_registry.RUNTIME.
# Values defined in policy_registry.py and documented in economic.md.
# Do NOT hardcode here — change values in policy_registry.py only.
#
# FAST:    1024  — conversation, emotional, fallback synthesis.
# GENERAL: 3072  — search synthesis, route queries, POI, code, analysis.
# HEAVY:   6144  — deep reasoning, long documents, heavy consensus tasks.
_MAX_TOKENS: dict[Tier, int] = {
    tier: RUNTIME.tier_configs[tier].max_output_tokens
    for tier in (Tier.FAST, Tier.GENERAL, Tier.HEAVY)
}

# Special-purpose model assignments (not tiers — utility roles)
# heavy_input_shaper uses llama-3.1-8b-instant NOT as Fast Tier
SHAPER_MODEL    = "llama-3.1-8b-instant"

# Agent Layer (models.md §AGENT LAYER) — tool-use execution fabric.
# These are NOT tier models — they have tool selection authority.
#
# ARCHITECTURE DECISION (май 2026):
# groq/compound and groq/compound-mini are NOT publicly available on Groq API
# (compound-mini: pricing TBD, not listed; compound: private beta).
# Calling them returns 404/401 → compound_agent falls to success=False → search_unavailable.
#
# Replacement: standard Groq models that support function calling via the same
# tool-use API (tool_choice="auto", tools=[...]).
# llama-3.1-8b-instant   — fast, low latency, supports function calling
# llama-3.3-70b-versatile — deep reasoning, multi-step, supports function calling
#
# No changes to compound_agent.py or groq_client.complete_with_tools() needed —
# the tool-use API contract is identical for all Groq models that support it.
FAST_AGENT_MODEL = "llama-3.1-8b-instant"    # replaces groq/compound-mini
DEEP_AGENT_MODEL = "llama-3.3-70b-versatile"  # replaces groq/compound

# Consensus arbiter — only active when Heavy Tier is NOT active (mutex)
CONSENSUS_MODEL = "openai/gpt-oss-120b"

# Multilingual normalization
MULTILINGUAL_ARABIC_MODEL = "allam-2-7b"
MULTILINGUAL_OTHER_MODEL  = "llama-3.3-70b-versatile"

# Long-context specialist (Heavy Tier secondary)
LONG_CONTEXT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Safety Gate models (Safety Layer — input firewall, NOT safety_agent)
SAFETY_PASS1_MODEL   = "meta-llama/llama-prompt-guard-2-22m"   # fast rejection filter
SAFETY_PASS2_MODELS  = [
    "meta-llama/llama-prompt-guard-2-86m",  # deep classification
    "openai/gpt-oss-safeguard-20b",          # final enforcement
]

# Speech models
WHISPER_PRIMARY  = "whisper-large-v3"
WHISPER_FAST     = "whisper-large-v3-turbo"
ORPHEUS_ENGLISH  = "canopylabs/orpheus-v1-english"
ORPHEUS_ARABIC   = "canopylabs/orpheus-arabic-saudi"

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