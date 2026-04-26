from __future__ import annotations

from typing import Any, Optional, Dict

from events.event_bus import EventBus
from events.event_store import EventStore


# =========================
# EVENT DISPATCHER
# =========================
class EventDispatcher:
    """
    ROLE:
    - unify event publishing
    - send events to EventBus (runtime)
    - persist events in EventStore (history)

    STRICT RULES:
    - no business logic
    - no branching
    - no event interpretation
    """

    def __init__(
        self,
        event_bus: EventBus,
        event_store: Optional[EventStore] = None,
    ):
        self._bus = event_bus
        self._store = event_store

    # =========================
    # DISPATCH
    # =========================
    def dispatch(
        self,
        event_name: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:

        # 1. publish to runtime subscribers
        self._bus.publish(event_name, payload)

        # 2. persist event (if store available)
        if self._store:
            self._store.append(event_name, payload)