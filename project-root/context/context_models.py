from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# =========================
# CONTEXT ITEM
# =========================

@dataclass
class ContextItem:
    """
    DTO: single retrieved document in LLM context
    """

    id: str
    source: str  # bm25 | vector | web
    content: str
    score: float


# =========================
# FULL CONTEXT
# =========================

@dataclass
class LLMContext:
    """
    DTO: final structured context passed to serializer/LLM
    """

    query: str
    items: List[ContextItem]
    token_estimate: Optional[int] = None


# =========================
# SERIALIZED CONTEXT
# =========================

@dataclass
class SerializedContext:
    """
    DTO: final serialized output for LLM input
    """

    format_type: str  # json | text
    payload: str