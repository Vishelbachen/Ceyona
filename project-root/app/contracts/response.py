from dataclasses import dataclass
from typing import Any, Optional, Dict, Union, Tuple


# ----------------------------
# BASE RESPONSE
# ----------------------------
@dataclass(frozen=True)
class BaseResponse:
    """
    Immutable base response.
    Core trace identity for full pipeline observability.
    """
    trace_id: str


# ----------------------------
# SUCCESS RESPONSE
# ----------------------------
@dataclass(frozen=True)
class SuccessResponse(BaseResponse):
    success: bool = True

    # 🧠 main output
    data: Optional[str] = None

    # 🧠 cognitive metadata
    model: Optional[str] = None
    intent: Optional[str] = None
    task_type: Optional[str] = None

    # 🧠 reasoning verification layer
    reasoning_valid: Optional[bool] = None

    # safe immutable structure
    reasoning_issues: Optional[Tuple[str, ...]] = None

    # 🧠 future quality scoring
    confidence: Optional[float] = None


# ----------------------------
# ERROR DETAIL
# ----------------------------
@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str
    layer: str

    context: Optional[Dict[str, Any]] = None


# ----------------------------
# ERROR RESPONSE
# ----------------------------
@dataclass(frozen=True)
class ErrorResponse(BaseResponse):
    success: bool = False

    error: Optional[ErrorDetail] = None

    retry_count: Optional[int] = None
    model: Optional[str] = None


# ----------------------------
# UNIFIED TYPE
# ----------------------------
OrchestratorResponse = Union[SuccessResponse, ErrorResponse]