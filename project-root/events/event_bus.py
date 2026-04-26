from __future__ import annotations

from typing import Callable, Dict, List, Any


# =========================
# EVENT BUS
# =========================
class EventBus:
    """
    ROLE:
    - lightweight in-process pub/sub
    - decouple components via events

    STRICT RULES:
    - no business logic
    - no async magic
    - no retries / queues
    - no delivery guarantees
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    # =========================
    # SUBSCRIBE
    # =========================
    def subscribe(
        self,
        event_name: str,
        handler: Callable[[Any], None],
    ) -> None:

        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(handler)

    # =========================
    # UNSUBSCRIBE (OPTIONAL)
    # =========================
    def unsubscribe(
        self,
        event_name: str,
        handler: Callable[[Any], None],
    ) -> None:

        if event_name not in self._subscribers:
            return

        try:
            self._subscribers[event_name].remove(handler)
        except ValueError:
            pass

    # =========================
    # PUBLISH
    # =========================
    def publish(
        self,
        event_name: str,
        payload: Any = None,
    ) -> None:

        handlers = self._subscribers.get(event_name, [])

        for handler in handlers:
            try:
                handler(payload)
            except Exception:
                # never break flow due to event handler
                pass

    # =========================
    # CLEAR (DEBUG / RESET)
    # =========================
    def clear(self) -> None:
        self._subscribers.clear()