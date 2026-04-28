from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# =========================
# CONTEXT INPUT CONTRACT
# =========================

@dataclass
class ContextInputContract:
    """
    DTO: input from retrieval/reranker into context layer
    """

    query: str
    documents: List[Dict[str, Any]]  # reranked docs


# =========================
# CONTEXT OUTPUT CONTRACT
# =========================

@dataclass
class ContextOutputContract:
    """
    DTO: structured context after assembly
    """

    query: str
    context_blocks: List[Dict[str, Any]]
    token_estimate: int


# =========================
# SERIALIZATION INPUT CONTRACT
# =========================

@dataclass
class SerializationInputContract:
    """
    DTO: input for context serializer
    """

    query: str
    context_blocks: List[Dict[str, Any]]


# =========================
# SERIALIZATION OUTPUT CONTRACT
# =========================

@dataclass
class SerializationOutputContract:
    """
    DTO: final serialized context for LLM
    """

    format_type: str  # json | text
    payload: str