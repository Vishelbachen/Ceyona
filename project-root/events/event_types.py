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
    BALANCE_CREDITED     = "balance.credited"
    BALANCE_EXHAUSTED    = "balance.exhausted"

    # safety
    SAFETY_BLOCK         = "safety.block"

    # requests
    REQUEST_COMPLETED    = "request.completed"
    REQUEST_DENIED       = "request.denied"


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


@dataclass
class BalanceCreditedEvent(BaseEvent):
    """Fired after a successful TON payment credit.

    payload keys:
        amount_usd      — credited amount (float)
        new_balance_usd — balance after credit (float)
        tx_hash         — TON transaction hash (str)
    """
    name: EventName = EventName.BALANCE_CREDITED


@dataclass
class BalanceExhaustedEvent(BaseEvent):
    """Fired when EPK denies a request due to insufficient_balance.

    payload keys:
        deny_reason — always "insufficient_balance" (str)
        intent      — classified intent string (str | None)
    """
    name: EventName = EventName.BALANCE_EXHAUSTED


@dataclass
class SafetyBlockEvent(BaseEvent):
    """Fired when safety_agent returns BLOCK verdict.

    payload keys:
        reason      — SafetyResult.reason text (str)
        tier        — execution tier (str)
    """
    name: EventName = EventName.SAFETY_BLOCK


@dataclass
class RequestCompletedEvent(BaseEvent):
    """Fired at the end of every successfully handled request.

    payload keys:
        intent          — classified intent (str)
        tier            — execution tier (str)
        model           — model used (str)
        total_cost_usd  — full request cost (float)
        latency_ms      — wall-clock latency (float)
    """
    name: EventName = EventName.REQUEST_COMPLETED


@dataclass
class RequestDeniedEvent(BaseEvent):
    """Fired when a request is denied (any deny_reason except balance exhausted,
    which fires BalanceExhaustedEvent instead).

    payload keys:
        deny_reason — reason string (str)
        intent      — classified intent or epk_decision string (str)
    """
    name: EventName = EventName.REQUEST_DENIED