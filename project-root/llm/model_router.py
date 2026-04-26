from __future__ import annotations

from typing import Literal, Dict


# =========================
# MODEL TIERS
# =========================
ModelTier = Literal["fast", "general", "heavy", "retrieval", "agent"]


# =========================
# MODEL ROUTER
# =========================
class ModelRouter:
    """
    ROLE:
    - deterministic mapping from task tier → model selection

    STRICT RULES:
    - no reasoning
    - no dynamic scoring
    - no prompt awareness
    - no memory access
    """

    def __init__(self):

        # FAST LAYER
        self._fast = "llama-3.1-8b-instant"
        self._fast_fallback = "groq/compound-mini"

        # GENERAL LAYER
        self._general_primary = "llama-3.3-70b-versatile"
        self._general_alt = "qwen/qwen3-32b"
        self._general_fallback = "openai/gpt-oss-20b"

        # HEAVY LAYER
        self._heavy_primary = "openai/gpt-oss-120b"
        self._heavy_alt = "llama-4-scout-17b-16e-instruct"
        self._heavy_exec = "groq/compound"

        # RETRIEVAL / HYBRID
        self._retrieval = "qwen/qwen3-32b"

        # AGENT LAYER
        self._agent = "llama-3.3-70b-versatile"

    # =========================
    # RESOLVE MODEL
    # =========================
    def resolve(self, tier: ModelTier, *, fallback: bool = True) -> str:

        if tier == "fast":
            return self._fast if not fallback else self._fast

        if tier == "general":
            return self._general_primary

        if tier == "heavy":
            return self._heavy_primary

        if tier == "retrieval":
            return self._retrieval

        if tier == "agent":
            return self._agent

        # safe fallback
        return self._general_primary

    # =========================
    # MULTI-OPTION (FOR ORCHESTRATOR FALLBACK LOGIC)
    # =========================
    def resolve_candidates(self, tier: ModelTier) -> Dict[str, str]:

        if tier == "fast":
            return {
                "primary": self._fast,
                "fallback": self._fast_fallback,
            }

        if tier == "general":
            return {
                "primary": self._general_primary,
                "alt": self._general_alt,
                "fallback": self._general_fallback,
            }

        if tier == "heavy":
            return {
                "primary": self._heavy_primary,
                "alt": self._heavy_alt,
                "exec": self._heavy_exec,
            }

        if tier == "retrieval":
            return {
                "primary": self._retrieval,
            }

        if tier == "agent":
            return {
                "primary": self._agent,
            }

        return {
            "primary": self._general_primary,
        }