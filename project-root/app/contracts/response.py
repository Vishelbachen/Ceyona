from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class SuccessResponse:
    success: bool = True
    data: Optional[Any] = None
    trace_id: Optional[str] = None

    def to_dict(self):
        return {
            "success": True,
            "data": self.data,
            "trace_id": self.trace_id
        }


@dataclass
class ErrorResponse:
    success: bool = False
    error: Any = None
    trace_id: Optional[str] = None

    def to_dict(self):
        return {
            "success": False,
            "error": self.error,
            "trace_id": self.trace_id
        }