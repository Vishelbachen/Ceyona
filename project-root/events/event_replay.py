from typing import List
from events.event_types import Event


class EventReplay:
    """
    Replays stored events for debugging / audit / recovery.
    """

    def replay(self, events: List[Event]):
        for event in events:
            self._handle(event)

    def _handle(self, event: Event):
        print(f"[REPLAY] {event.type} | user={event.user_id} | payload={event.payload}")