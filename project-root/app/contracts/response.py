from dataclasses import dataclass
from typing import Any, Optional, Dict, Union, List


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
    """
    Structured success response with cognitive metadata.
    """

    success: bool = True

    # 🧠 main output
    data: Optional[str] = None

    # 🧠 cognitive metadata (VERY IMPORTANT FOR FUTURE LAYERS)
    model: Optional[str] = None
    intent: Optional[str] = None
    task_type: Optional[str] = None

    # 🧠 reasoning layer output (verifier integration)
    reasoning_valid: Optional[bool] = None
    reasoning_issues: Optional[List[str]] = None

    # 🧠 optional quality scoring (future self-evaluation)
    confidence: Optional[float] = None


# ----------------------------
# ERROR DETAIL
# ----------------------------
@dataclass(frozen=True)
class ErrorDetail:
    code: str
    message: str
    layer: str

    # 🧠 debug context (VERY useful for production tracing)
    context: Optional[Dict[str, Any]] = None


# ----------------------------
# ERROR RESPONSE
# ----------------------------
@dataclass(frozen=True)
class ErrorResponse(BaseResponse):
    success: bool = False

    error: ErrorDetail = None

    # 🧠 optional system diagnostics
    retry_count: Optional[int] = None
    model: Optional[str] = None


# ----------------------------
# UNIFIED TYPE
# ----------------------------
OrchestratorResponse = Union[SuccessResponse, ErrorResponse]