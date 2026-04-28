from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# =========================
# RAW QUERY CONTRACT
# =========================

@dataclass
class RawQueryContract:
    """
    DTO: incoming raw user query
    """

    query: str
    metadata: Optional[Dict[str, Any]] = None


# =========================
# RETRIEVAL INPUT CONTRACT
# =========================

@dataclass
class RetrievalInputContract:
    """
    DTO: normalized input for retrieval layer
    """

    query: str
    tokens: List[str]
    embedding: Optional[List[float]] = None


# =========================
# RETRIEVAL OUTPUT CONTRACT
# =========================

@dataclass
class RetrievalOutputContract:
    """
    DTO: output from retrieval engine before reranking
    """

    query: str
    results: Dict[str, List[Dict[str, Any]]]  # bm25 / vector / web
    top_k: int


# =========================
# RERANK INPUT CONTRACT
# =========================

@dataclass
class RerankInputContract:
    """
    DTO: input for cross-encoder reranker
    """

    query: str
    documents: List[Dict[str, Any]]


# =========================
# FINAL RETRIEVAL CONTRACT
# =========================

@dataclass
class FinalRetrievalContract:
    """
    DTO: final ranked output after reranking
    """

    query: str
    documents: List[Dict[str, Any]]