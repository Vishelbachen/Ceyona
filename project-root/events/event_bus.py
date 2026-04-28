from typing import List, Callable
from events.event_types import Event


class EventBus:
    """
    In-memory event bus (v4.7 minimal implementation)
    """

    def __init__(self):
        self.subscribers: List[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]):
        self.subscribers.append(handler)

    def publish(self, event: Event):
        for handler in self.subscribers:
            handler(event)