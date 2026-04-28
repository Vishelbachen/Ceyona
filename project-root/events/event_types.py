from dataclasses import dataclass
from typing import Literal, Dict, Any


# =========================
# CORE EVENT TYPE DEFINITIONS
# =========================

EventType = Literal[
    "request_received",
    "auth_failed",
    "auth_success",
    "update_normalized",
    "message_routed",
    "callback_received",
    "execution_started",
    "execution_completed",
    "epk_decision_made",
    "policy_selected",
    "agent_invoked",
    "retrieval_called",
    "memory_written",
    "response_generated",
    "error_occurred",
]


@dataclass(frozen=True)
class Event:
    """
    AI Platform v4.7 — Event Contract

    STRICT RULES:
    - Immutable structure
    - No logic
    - No behavior
    - Only data schema definition
    """

    type: EventType
    payload: Dict[str, Any]
    timestamp: str
    source: str