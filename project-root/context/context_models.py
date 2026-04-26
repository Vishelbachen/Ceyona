from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# =========================
# CONTEXT UNIT (ATOMIC BLOCK)
# =========================
@dataclass(frozen=True)
class ContextUnit:
    """
    ROLE:
    - smallest semantic-safe unit passed to LLM
    - produced by ContextAssembler

    STRICT RULE:
    - no logic
    - no ranking
    """

    text: str
    source_id: Optional[int] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# =========================
# CONTEXT DOCUMENT
# =========================
@dataclass(frozen=True)
class ContextDocument:
    """
    ROLE:
    - structured collection of ContextUnits
    - represents full retrieval-to-LLM context

    USED BY:
    - prompt_engine
    """

    units: List[ContextUnit]
    total_units: int
    estimated_tokens: Optional[int] = None


# =========================
# CONTEXT INPUT WRAPPER
# =========================
@dataclass(frozen=True)
class ContextInput:
    """
    ROLE:
    - input contract for context layer

    SOURCE:
    - orchestrator / retrieval pipeline
    """

    query: str
    raw_retrieval: List[Dict[str, Any]]
    max_tokens: int


# =========================
# CONTEXT OUTPUT WRAPPER
# =========================
@dataclass(frozen=True)
class ContextOutput:
    """
    ROLE:
    - final output from context layer to LLM layer
    """

    system_prompt: str
    user_prompt: str
    context: ContextDocument


# =========================
# CONTEXT DEBUG METRICS
# =========================
@dataclass(frozen=True)
class ContextMetrics:
    """
    ROLE:
    - observability only
    """

    truncated: bool
    input_items: int
    output_units: int