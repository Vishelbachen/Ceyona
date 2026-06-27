import logging

from events.event_bus import EventBus
from events.event_store import EventStore
from events.event_types import (
    BaseEvent,
    EventName,
)

logger = logging.getLogger(__name__)


async def _log_handler(event: BaseEvent) -> None:
    """Structured log for every event — observability only."""
    logger.info(
        "event",
        extra={
            "event_id":  event.event_id,
            "name":      event.name,
            "user_id":   event.user_id,
            "payload":   event.payload,
            "timestamp": event.timestamp.isoformat(),
        },
    )


def setup_dispatcher(bus: EventBus, store: EventStore) -> None:
    """
    Register all system handlers on the bus.
    Call once from bootstrap.py after Redis is ready.
    """
    from notifications.event_notifier import event_notifier

    async def _store_handler(event: BaseEvent) -> None:
        await store.append(event)

    # ── wildcard: every event → structured log + persistent store ────────────
    bus.subscribe_all(_log_handler)
    bus.subscribe_all(_store_handler)

    # ── balance.credited → email notification ────────────────────────────────
    async def _on_balance_credited(event: BaseEvent) -> None:
        await event_notifier.on_balance_credited(
            user_id=event.user_id,
            amount_usd=event.payload.get("amount_usd", 0.0),
            new_balance_usd=event.payload.get("new_balance_usd", 0.0),
        )

    bus.subscribe(EventName.BALANCE_CREDITED, _on_balance_credited)

    # ── balance.exhausted → email notification ───────────────────────────────
    async def _on_balance_exhausted(event: BaseEvent) -> None:
        await event_notifier.on_balance_exhausted(
            user_id=event.user_id,
        )

    bus.subscribe(EventName.BALANCE_EXHAUSTED, _on_balance_exhausted)

    # ── safety.block → log notification ─────────────────────────────────────
    async def _on_safety_block(event: BaseEvent) -> None:
        await event_notifier.on_safety_block(
            user_id=event.user_id,
            reason=event.payload.get("reason", "unknown"),
        )

    bus.subscribe(EventName.SAFETY_BLOCK, _on_safety_block)

    logger.info("EventDispatcher: handlers registered")