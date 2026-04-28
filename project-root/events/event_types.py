from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


# ─── EVENT NAMES ─────────────────────────────────────────────────────────────

class EventName(str, Enum):
    # transport
    UPDATE_RECEIVED      = "update.received"
    UPDATE_REJECTED      = "update.rejected"

    # auth
    AUTH_PASSED          = "auth.passed"
    AUTH_FAILED          = "auth.failed"

    # EPK
    EPK_ALLOW            = "epk.allow"
    EPK_DENY             = "epk.deny"
    EPK_DEGRADE          = "epk.degrade"

    # execution
    EXECUTION_STARTED    = "execution.started"
    EXECUTION_COMPLETED  = "execution.completed"
    EXECUTION_FAILED     = "execution.failed"

    # LLM
    LLM_CALLED           = "llm.called"
    LLM_FALLBACK         = "llm.fallback"

    # retrieval
    RETRIEVAL_STARTED    = "retrieval.started"
    RETRIEVAL_COMPLETED  = "retrieval.completed"

    # memory
    MEMORY_READ          = "memory.read"
    MEMORY_WRITTEN       = "memory.written"

    # payments
    BALANCE_CHECKED      = "balance.checked"
    BALANCE_DEDUCTED     = "balance.deducted"
    BALANCE_INSUFFICIENT = "balance.insufficient"


# ─── BASE EVENT ───────────────────────────────────────────────────────────────

@dataclass
class BaseEvent:
    name: EventName
    user_id: int | None = None
    payload: dict = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── TYPED EVENTS ────────────────────────────────────────────────────────────

@dataclass
class UpdateReceivedEvent(BaseEvent):
    name: EventName = EventName.UPDATE_RECEIVED


@dataclass
class AuthFailedEvent(BaseEvent):
    name: EventName = EventName.AUTH_FAILED


@dataclass
class EPKDecisionEvent(BaseEvent):
    """Covers ALLOW / DENY / DEGRADE — set name accordingly."""
    name: EventName = EventName.EPK_ALLOW


@dataclass
class ExecutionCompletedEvent(BaseEvent):
    name: EventName = EventName.EXECUTION_COMPLETED


@dataclass
class ExecutionFailedEvent(BaseEvent):
    name: EventName = EventName.EXECUTION_FAILED


@dataclass
class LLMCalledEvent(BaseEvent):
    name: EventName = EventName.LLM_CALLED


@dataclass
class LLMFallbackEvent(BaseEvent):
    name: EventName = EventName.LLM_FALLBACK


@dataclass
class BalanceDeductedEvent(BaseEvent):
    name: EventName = EventName.BALANCE_DEDUCTED


@dataclass
class BalanceInsufficientEvent(BaseEvent):
    name: EventName = EventName.BALANCE_INSUFFICIENT