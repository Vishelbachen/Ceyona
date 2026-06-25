from __future__ import annotations

from contracts.shared_types import Tier
from core.kernel.policy_registry import RUNTIME

# ─── MODEL REGISTRY ───────────────────────────────────────────────────────
# Source of truth for all model assignments per tier.
# Matches models.md v9.0 (Post-Deprecation Migration Edition).
#
# Deprecated models removed (Groq announcement Jun 17, 2026):
#   llama-3.1-8b-instant          → deprecated Aug 16, 2026
#   llama-3.3-70b-versatile       → deprecated Aug 16, 2026
#   qwen/qwen3-32b                → deprecated Jul 17, 2026
#   llama-4-scout-17b-16e-instruct → deprecated Jul 17, 2026

# Primary model per tier — used by default in all agent calls
_PRIMARY: dict[Tier, str] = {
    Tier.FAST:    "openai/gpt-oss-20b",
    Tier.GENERAL: "qwen/qwen3.6-27b",
    Tier.HEAVY:   "openai/gpt-oss-120b",
}

# All models available per tier (primary first)
_TIER_MODELS: dict[Tier, list[str]] = {
    Tier.FAST: [
        "openai/gpt-oss-20b",   # primary: ~1000 TPS, MoE 21B/3.6B active, reasoning_effort="low"
    ],
    Tier.GENERAL: [
        "qwen/qwen3.6-27b",        # primary: IFEval 95.0, 201 langs, vision, 262K ctx
                                    # CRITICAL: reasoning_effort="none" mandatory at every call site
                                    # params: temperature=0.7, top_p=0.80, presence_penalty=1.5
                                    # NOTE: top_k omitted — not supported by Groq OpenAI-compatible API
        "openai/gpt-oss-120b",     # fallback: if qwen3.6-27b unavailable (models.md §3)
    ],
    Tier.HEAVY: [
        "openai/gpt-oss-120b",  # primary: deep multi-step reasoning + consensus arbiter
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
# heavy_input_shaper uses gpt-oss-20b NOT as Fast Tier — utility role only
# reasoning_effort="low" mandatory here too (models.md §5)
SHAPER_MODEL = "openai/gpt-oss-20b"

# Agent Layer (models.md §AGENT LAYER) — tool-use execution fabric.
# These are NOT tier models — they have tool selection authority.
#
# CONFIRMED (май 2026): groq/compound и groq/compound-mini подтверждены
# ДОСТУПНЫМИ на аккаунте (см. available_models list, models1.md §22).
# Предыдущая гипотеза о недоступности (404/401) — ОПРОВЕРГНУТА.
# Причина бага 13.1 — не модели. Диагноз: audit.md §13.1 (уточнённый).
#
# groq/compound-mini → AgentType.COMPOUND_FAST (Tier.FAST path)
# groq/compound      → AgentType.COMPOUND_DEEP (Tier.GENERAL path)
FAST_AGENT_MODEL = "groq/compound-mini"   # AgentType.COMPOUND_FAST
DEEP_AGENT_MODEL = "groq/compound"        # AgentType.COMPOUND_DEEP

# Consensus arbiter — only active when Heavy Tier is NOT active (mutex)
CONSENSUS_MODEL = "openai/gpt-oss-120b"

# Multilingual normalization
MULTILINGUAL_ARABIC_MODEL = "allam-2-7b"
MULTILINGUAL_OTHER_MODEL = "qwen/qwen3.6-27b"  # 201 languages, replaces llama-3.3-70b-versatile

# Long-context specialist — qwen3.6-27b has 262K native ctx (Groq limit: 131K)
# Replaces llama-4-scout-17b-16e-instruct (deprecated Jul 17, 2026)
LONG_CONTEXT_MODEL = "qwen/qwen3.6-27b"

# Safety Gate models (Safety Layer — input firewall, NOT safety_agent)
SAFETY_PASS1_MODEL = "meta-llama/llama-prompt-guard-2-22m"   # fast rejection filter
SAFETY_PASS2_MODELS = [
    "meta-llama/llama-prompt-guard-2-86m",  # deep classification
    "openai/gpt-oss-safeguard-20b",          # final enforcement
]

# Speech models
WHISPER_PRIMARY = "whisper-large-v3"
WHISPER_FAST = "whisper-large-v3-turbo"
ORPHEUS_ENGLISH = "canopylabs/orpheus-v1-english"
ORPHEUS_ARABIC = "canopylabs/orpheus-arabic-saudi"

# qwen models with thinking mode — MUST have thinking disabled at every call site
# qwen3-32b: deprecated Jul 17, kept here until removal in case of emergency fallback
# qwen3.6-27b: new GENERAL primary — reasoning_effort="none" is the Groq API equivalent
QWEN_THINKING_DISABLED_MODELS: frozenset[str] = frozenset({
    "qwen/qwen3-32b",     # deprecated Jul 17, 2026
    "qwen/qwen3.6-27b",   # GENERAL primary — thinking: False mandatory (models.md §3)
})


# ─── PUBLIC API ───────────────────────────────────────────────────────────

def route_model(tier: Tier, preferred_model: str | None = None) -> str:
    """
    Return the model to use for the given tier.

    If preferred_model is set and available in _TIER_MODELS[tier], use it.
    Otherwise fall back to the tier primary (architecture.md §45.3).

    preferred_model is an intent-based hint from RoutingProfile — never a
    hard directive. model_router is the sole model selection authority (§8).
    """
    if preferred_model and preferred_model in _TIER_MODELS.get(tier, []):
        return preferred_model
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


def get_primary_model(tier: Tier) -> str:
    """Alias for route_model; kept for readable call sites."""
    return route_model(tier)


def requires_thinking_disabled(model: str) -> bool:
    """
    Return True if the model must have thinking mode explicitly disabled.
    Applies to qwen/qwen3-32b — thinking: False must be enforced at call site.
    """
    return model in QWEN_THINKING_DISABLED_MODELS


__all__ = [
    "SHAPER_MODEL",
    "FAST_AGENT_MODEL",
    "DEEP_AGENT_MODEL",
    "CONSENSUS_MODEL",
    "MULTILINGUAL_ARABIC_MODEL",
    "MULTILINGUAL_OTHER_MODEL",
    "LONG_CONTEXT_MODEL",
    "SAFETY_PASS1_MODEL",
    "SAFETY_PASS2_MODELS",
    "WHISPER_PRIMARY",
    "WHISPER_FAST",
    "ORPHEUS_ENGLISH",
    "ORPHEUS_ARABIC",
    "QWEN_THINKING_DISABLED_MODELS",
    "route_model",
    "get_primary_model",
    "route_max_tokens",
    "get_tier_models",
    "requires_thinking_disabled",
]