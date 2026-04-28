from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    RETRIEVAL_DONE = "retrieval_done"
    CONTEXT_BUILT = "context_built"
    MODEL_INVOKED = "model_invoked"
    RESPONSE_READY = "response_ready"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    type: EventType
    user_id: str
    payload: dict[str, Any]
    error: Optional[str] = None