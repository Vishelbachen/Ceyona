from typing import List
from events.event_types import Event


class EventStore:
    """
    Append-only event storage (in-memory for now)
    """

    def __init__(self):
        self._events: List[Event] = []

    def append(self, event: Event):
        self._events.append(event)

    def all(self) -> List[Event]:
        return self._events