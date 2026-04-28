from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# =========================
# QUERY MODEL
# =========================

@dataclass
class RetrievalQuery:
    """
    DTO: normalized retrieval query container
    """

    raw_query: str
    normalized_query: str
    tokens: List[str]
    metadata: Dict[str, Any]


# =========================
# DOCUMENT MODEL
# =========================

@dataclass
class RetrievalDocument:
    """
    DTO: unified representation of retrieved document
    """

    id: str
    source: str  # bm25 | vector | web
    title: Optional[str]
    content: str
    score: float


# =========================
# RESULT SET
# =========================

@dataclass
class RetrievalResult:
    """
    DTO: aggregated retrieval result container
    """

    query: str
    documents: List[RetrievalDocument]
    total: int


# =========================
# RAW SOURCE WRAPPER
# =========================

@dataclass
class RawRetrievalSource:
    """
    DTO: raw output from retrieval backends before reranking
    """

    bm25: List[Dict[str, Any]]
    vector: List[Dict[str, Any]]
    web: List[Dict[str, Any]]