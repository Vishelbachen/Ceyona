from dataclasses import dataclass
from typing import Any, Optional, Dict, Union


# ----------------------------
# BASE RESPONSE
# ----------------------------

@dataclass(frozen=True)
class BaseResponse:
    """
    Immutable base response.
    Ensures trace consistency and prevents runtime mutation bugs.
    """
    trace_id: str


# ----------------------------
# SUCCESS RESPONSE
# ----------------------------

@dataclass(frozen=True)
class SuccessResponse(BaseResponse):
    """
    Strict success contract.

    Guarantees:
    - success is ALWAYS True
    - data is always explicit (can be None, but explicit)
    """
    success: bool = True
    data: Optional[str] = None


# ----------------------------
# ERROR RESPONSE
# ----------------------------

@dataclass(frozen=True)
class ErrorDetail:
    """
    Structured error payload.
    """

    code: str
    message: str
    layer: str
    data: Optional[Any] = None


@dataclass(frozen=True)
class ErrorResponse(BaseResponse):
    """
    Strict error contract.

    Guarantees:
    - success is ALWAYS False
    - error is structured, never raw string
    """

    success: bool = False
    error: ErrorDetail = None


# ----------------------------
# TYPE UNIFICATION
# ----------------------------

OrchestratorResponse = Union[SuccessResponse, ErrorResponse]