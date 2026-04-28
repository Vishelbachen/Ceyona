from events.event_bus import EventBus
from events.event_store import EventStore
from events.event_types import Event


class EventDispatcher:
    """
    Bridges EventBus and EventStore
    """

    def __init__(self, bus: EventBus, store: EventStore):
        self.bus = bus
        self.store = store

    def dispatch(self, event: Event):
        self.store.append(event)
        self.bus.publish(event)