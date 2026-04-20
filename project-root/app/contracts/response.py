from dataclasses import dataclass
from typing import Any, Optional, Dict, Union, Tuple


# ----------------------------
# BASE RESPONSE
# ----------------------------
@dataclass(frozen=True)
class BaseResponse:
    trace_id: str


# ----------------------------
# SUCCESS RESPONSE
# ----------------------------
@dataclass(frozen=True)
class SuccessResponse(BaseResponse):

    data: Optional[str] = None

    model: Optional[str] = None
    intent: Optional[str] = None
    task_type: Optional[str] = None

    reasoning_valid: Optional[bool] = None

    # ALWAYS IMMUTABLE TUPLE
    reasoning_issues: Tuple[str, ...] = ()

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

    error: Optional[ErrorDetail] = None

    retry_count: Optional[int] = None
    model: Optional[str] = None


# ----------------------------
# UNIFIED TYPE
# ----------------------------
OrchestratorResponse = Union[SuccessResponse, ErrorResponse]