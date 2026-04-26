from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# =========================
# EVENT NAMES (CONTRACT)
# =========================
class EventTypes:
    """
    Centralized event naming.

    STRICT RULES:
    - no logic
    - no behavior
    - constants only
    """

    # =========================
    # SYSTEM
    # =========================
    REQUEST_STARTED = "request_started"
    REQUEST_FINISHED = "request_finished"
    REQUEST_FAILED = "request_failed"

    # =========================
    # COGNITION
    # =========================
    INTENT_DETECTED = "intent_detected"
    REASONING_COMPLETED = "reasoning_completed"

    # =========================
    # AGENTS
    # =========================
    AGENT_SELECTED = "agent_selected"
    AGENT_COMPLETED = "agent_completed"

    # =========================
    # RESPONSE
    # =========================
    RESPONSE_READY = "response_ready"

    # =========================
    # MEMORY
    # =========================
    MEMORY_READ = "memory_read"
    MEMORY_WRITTEN = "memory_written"

    # =========================
    # EXTERNAL
    # =========================
    EXTERNAL_CALL = "external_call"
    EXTERNAL_ERROR = "external_error"

    # =========================
    # PAYMENTS
    # =========================
    PAYMENT_CHECK = "payment_check"
    PAYMENT_FAILED = "payment_failed"


# =========================
# BASE EVENT (OPTIONAL STRUCTURE)
# =========================
@dataclass
class BaseEvent:
    """
    Optional typed event structure.

    NOTE:
    - purely structural
    - no behavior
    """

    name: str
    payload: Optional[Dict[str, Any]] = None