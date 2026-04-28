from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


# =========================
# GENERIC ID TYPES
# =========================

ID = str
JSON = Dict[str, Any]


# =========================
# SCORE TYPE
# =========================

Score = float


# =========================
# METADATA CONTAINER
# =========================

Metadata = Dict[str, Any]


# =========================
# GENERIC DOCUMENT TYPE
# =========================

@dataclass
class Document:
    """
    Universal document structure across all layers
    """

    id: ID
    content: str
    metadata: Optional[Metadata] = None


# =========================
# QUERY TYPE
# =========================

@dataclass
class Query:
    """
    Universal query representation
    """

    text: str
    metadata: Optional[Metadata] = None


# =========================
# EMBEDDING TYPE
# =========================

Embedding = List[float]


# =========================
# RESULT WRAPPER
# =========================

@dataclass
class Result:
    """
    Generic result wrapper for system-wide usage
    """

    id: ID
    score: Score
    payload: Optional[JSON] = None