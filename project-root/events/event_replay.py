from __future__ import annotations

from typing import Optional, Dict, Any, List

from events.event_bus import EventBus
from events.event_store import EventStore


# =========================
# EVENT REPLAY
# =========================
class EventReplay:
    """
    ROLE:
    - replay stored events through EventBus

    USE CASES:
    - debugging
    - system warmup
    - re-trigger side effects

    STRICT RULES:
    - no business logic
    - no event modification
    - no state reconstruction logic
    """

    def __init__(
        self,
        event_bus: EventBus,
        event_store: EventStore,
    ):
        self._bus = event_bus
        self._store = event_store

    # =========================
    # REPLAY ALL
    # =========================
    def replay_all(self) -> None:
        events = self._store.get_all()

        for event in events:
            self._bus.publish(
                event_name=event["event"],
                payload=event.get("payload"),
            )

    # =========================
    # REPLAY BY EVENT NAME
    # =========================
    def replay_by_event(
        self,
        event_name: str,
        limit: int = 50,
    ) -> None:

        events = self._store.get_by_event(event_name, limit=limit)

        for event in events:
            self._bus.publish(
                event_name=event["event"],
                payload=event.get("payload"),
            )

    # =========================
    # REPLAY CUSTOM LIST
    # =========================
    def replay(
        self,
        events: List[Dict[str, Any]],
    ) -> None:

        for event in events:
            self._bus.publish(
                event_name=event["event"],
                payload=event.get("payload"),
            )