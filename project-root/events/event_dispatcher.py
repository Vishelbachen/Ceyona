from typing import Any, Dict

from events.event_bus import EventBus
from events.event_store import EventStore


class EventDispatcher:
    """
    AI Platform v4.7 — Event Dispatcher

    RESPONSIBILITY:
    - Bridge between system components and event system
    - Publish events to EventBus
    - Persist events to EventStore

    STRICT RULES:
    - No business logic
    - No event interpretation
    - No routing decisions
    - No LLM / retrieval / memory access
    """

    def __init__(self, event_bus: EventBus, event_store: EventStore):
        self.event_bus = event_bus
        self.event_store = event_store

    def dispatch(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Synchronous event dispatch:
        - store event
        - publish event
        """

        # =========================
        # 1. PERSIST EVENT
        # =========================
        event_id = self.event_store.append(
            event_type=event_type,
            payload=payload,
        )

        # =========================
        # 2. BROADCAST EVENT
        # =========================
        self.event_bus.publish(
            event_type=event_type,
            event={
                "id": event_id,
                "type": event_type,
                "payload": payload,
            },
        )

        return event_id

    async def dispatch_async(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Async version of dispatch.
        """

        event_id = self.event_store.append(
            event_type=event_type,
            payload=payload,
        )

        await self.event_bus.publish_async(
            event_type=event_type,
            event={
                "id": event_id,
                "type": event_type,
                "payload": payload,
            },
        )

        return event_id