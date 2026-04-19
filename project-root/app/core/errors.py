from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class AppError:
    code: str
    message: str
    layer: str
    trace_id: Optional[str] = None
    data: Optional[Any] = None

    def to_dict(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "layer": self.layer,
                "trace_id": self.trace_id,
                "data": self.data,
            }
        }