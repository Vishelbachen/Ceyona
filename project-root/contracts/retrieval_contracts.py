from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# =========================
# INPUT CONTRACT
# =========================
@dataclass(frozen=True)
class RetrievalRequest:
    """
    ROLE:
    - strict input schema for retrieval engine

    USED BY:
    - orchestrator
    - context assembler
    """

    query: str
    top_k: int = 10
    use_cache: bool = True


# =========================
# RAW RETRIEVAL ITEM
# =========================
@dataclass(frozen=True)
class RetrievalItem:
    """
    ROLE:
    - unified representation of BM25 / Dense / fused results
    """

    id: int
    score: float
    source: str  # "sparse" | "dense" | "hybrid"
    metadata: Optional[Dict[str, Any]] = None


# =========================
# RETRIEVAL RESPONSE
# =========================
@dataclass(frozen=True)
class RetrievalResponse:
    """
    ROLE:
    - final output contract from RetrievalEngine

    STRICT:
    - no raw text
    - no embeddings
    - no interpretation
    """

    items: List[RetrievalItem]
    took_ms: Optional[int] = None
    cache_hit: bool = False


# =========================
# INTERNAL PIPELINE STATE
# =========================
@dataclass(frozen=True)
class RetrievalPipelineState:
    """
    ROLE:
    - internal tracking for debugging / observability only
    """

    query: str
    bm25_hits: int
    dense_hits: int
    fused_hits: int
    reranked: bool