from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    FAST    = "FAST"
    GENERAL = "GENERAL"
    HEAVY   = "HEAVY"


class Complexity(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class EPKDecision(str, Enum):
    ALLOW          = "ALLOW"
    DENY           = "DENY"
    DEGRADED_MODE  = "DEGRADED_MODE"
    HEAVY_REQUIRED = "HEAVY_REQUIRED"


class TruthMode(str, Enum):
    STRICT     = "strict"      # только факты из context — без context = блок
    HYBRID     = "hybrid"      # LLM может дополнять, но context приоритетен
    GENERATIVE = "generative"  # свободная генерация (creative, conversation)


class ReasoningDepth(str, Enum):
    """
    Capability axis: how much structured reasoning the request requires.
    Decoupled from Intent — the same intent can have different depths
    depending on actual request content.

    NONE  — conversational, emotional, simple factual replies.
    LIGHT — general knowledge, descriptive search, media recall, code.
    HEAVY — constraint satisfaction, proofs, multi-step logic, exams.
    """
    NONE  = "none"
    LIGHT = "light"
    HEAVY = "heavy"


class DomainHint(str, Enum):
    """
    Domain axis: what kind of knowledge / pipeline the request draws on.
    Used by reasoning_engine and coordinator — NOT a routing decision by itself.

    GENERAL — default; no specialised pipeline.
    MATH    — constraint satisfaction, symbolic reasoning, verification loop.
    CODE    — software engineering, debugging, architecture.
    MEDIA   — film, anime, music, game identification or recall.
    GEO     — maps, routes, weather, location facts.
    """
    GENERAL = "general"
    MATH    = "math"
    CODE    = "code"
    MEDIA   = "media"
    GEO     = "geo"


@dataclass(frozen=True)
class RoutingProfile:
    """
    Capability descriptor produced by _resolve_routing() in intent_engine.
    Consumed by reasoning_engine, coordinator, orchestrator, and assembler.

    This is the policy layer between Intent (signal) and Pipeline (execution).
    Intent is preserved as an observability signal — it does NOT select the
    pipeline directly. RoutingProfile owns that decision.

    Fields
    ------
    retrieval_required : bool
        True  → orchestrator MUST fetch external context before LLM call.
        False → request is self-contained; no retrieval needed.
    reasoning_depth : ReasoningDepth
        Selects the reasoning strategy axis in reasoning_engine.
    domain_hint : DomainHint
        Selects the specialised pipeline branch (MATH verification loop, etc.).
    truth_mode : TruthMode
        Declared here — assembler reads it from RoutingProfile, not from Intent.
    """
    retrieval_required: bool
    reasoning_depth:    ReasoningDepth
    domain_hint:        DomainHint
    truth_mode:         TruthMode