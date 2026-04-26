from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable, Awaitable


# =========================
# EVENT NOTIFIER
# =========================
class EventNotifier:
    """
    ROLE:
    - publish system events to external subscribers
    - act as async side-effect dispatcher

    STRICT RULES:
    - no business logic
    - no event generation logic
    - no filtering decisions
    - no persistence (event_store handles that)
    """

    def __init__(self):
        # subscribers: event_type -> list of callbacks
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Awaitable[None]]]] = {}

    # =========================
    # SUBSCRIBE
    # =========================
    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
    ) -> None:

        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)

    # =========================
    # PUBLISH EVENT
    # =========================
    async def publish(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:

        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            return

        # fan-out dispatch (fire-and-forget style)
        for handler in handlers:
            await handler(payload)

    # =========================
    # SAFE EMIT (OPTIONAL WRAPPER)
    # =========================
    async def emit_safe(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Defensive wrapper to avoid breaking core flow if a handler fails.
        """

        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            try:
                await handler(payload)
            except Exception:
                # intentionally swallowed: notifications must not break system
                continue