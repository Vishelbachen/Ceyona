import logging

from events.event_bus import EventBus
from events.event_store import EventStore
from events.event_types import BaseEvent

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

    async def _store_handler(event: BaseEvent) -> None:
        await store.append(event)

    # every event → structured log
    bus.subscribe_all(_log_handler)

    # every event → persistent store
    bus.subscribe_all(_store_handler)

    logger.info("EventDispatcher: handlers registered")