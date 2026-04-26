from __future__ import annotations

from typing import List, Dict, Any, Optional
import time


# =========================
# EVENT STORE
# =========================
class EventStore:
    """
    ROLE:
    - persist events (in-memory or pluggable storage)
    - provide event history

    STRICT RULES:
    - no business logic
    - no event interpretation
    - no orchestration
    """

    def __init__(self, max_events: int = 1000):
        self._events: List[Dict[str, Any]] = []
        self._max_events = max_events

    # =========================
    # APPEND EVENT
    # =========================
    def append(
        self,
        event_name: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:

        event = {
            "event": event_name,
            "payload": payload or {},
            "timestamp": time.time(),
        }

        self._events.append(event)

        # FIFO limit
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    # =========================
    # GET ALL EVENTS
    # =========================
    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._events)

    # =========================
    # FILTER BY EVENT NAME
    # =========================
    def get_by_event(
        self,
        event_name: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        results = [
            e for e in self._events
            if e["event"] == event_name
        ]

        return results[-limit:]

    # =========================
    # CLEAR STORE
    # =========================
    def clear(self) -> None:
        self._events.clear()

    # =========================
    # SIZE
    # =========================
    def size(self) -> int:
        return len(self._events)