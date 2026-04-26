from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


# =========================
# GENERIC IDENTIFIERS
# =========================
UserId = str
SessionId = str
DocumentId = int


# =========================
# GENERIC PAYLOAD
# =========================
JSONDict = Dict[str, Any]
JSONList = List[Any]
JSONValue = Union[str, int, float, bool, None, JSONDict, JSONList]


# =========================
# TIMING TYPE
# =========================
Timestamp = float  # unix time


# =========================
# GENERIC RESULT WRAPPER
# =========================
@dataclass(frozen=True)
class Result:
    """
    ROLE:
    - universal success/failure wrapper
    - used across services and infra layers

    STRICT RULE:
    - no domain logic
    """

    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# =========================
# PAGINATION
# =========================
@dataclass(frozen=True)
class Page:
    """
    ROLE:
    - generic pagination contract
    """

    limit: int
    offset: int


# =========================
# RUNTIME CONTEXT FLAGS
# =========================
@dataclass(frozen=True)
class RuntimeFlags:
    """
    ROLE:
    - system-level execution toggles
    """

    debug: bool = False
    safe_mode: bool = True
    tracing: bool = False