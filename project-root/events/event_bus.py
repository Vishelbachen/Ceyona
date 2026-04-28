import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from events.event_types import BaseEvent, EventName

logger = logging.getLogger(__name__)

Handler = Callable[[BaseEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[EventName, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    def subscribe(self, event_name: EventName, handler: Handler) -> None:
        """Register a handler for a specific event name."""
        self._handlers[event_name].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Register a handler that receives every event (useful for loggers)."""
        self._wildcard.append(handler)

    async def publish(self, event: BaseEvent) -> None:
        """
        Fire event to all subscribers.
        Always non-blocking — handlers run as background tasks.
        publish() itself never raises.
        """
        handlers = self._handlers.get(event.name, []) + self._wildcard

        for handler in handlers:
            asyncio.create_task(self._safe_call(handler, event))

    @staticmethod
    async def _safe_call(handler: Handler, event: BaseEvent) -> None:
        try:
            await handler(event)
        except Exception as exc:
            logger.warning(
                "Event handler failed",
                extra={
                    "handler": handler.__qualname__,
                    "event": event.name,
                    "error": str(exc),
                },
            )


# Singleton
event_bus = EventBus()