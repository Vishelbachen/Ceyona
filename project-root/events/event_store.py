from typing import Any, Dict, List, Optional
from datetime import datetime


class EventStore:
    """
    AI Platform v4.7 — Event Store (Append-only log)

    RESPONSIBILITY:
    - Persist all system events
    - Provide audit trail
    - Enable replay/debugging

    STRICT RULES:
    - No business logic
    - No event interpretation
    - No routing decisions
    - No LLM / retrieval / memory logic
    """

    def __init__(self):
        # In-memory fallback store (can be replaced by DB)
        self._events: List[Dict[str, Any]] = []

    def append(self, event_type: str, payload: Dict[str, Any]) -> str:
        """
        Store event in immutable log.
        """

        event_id = f"evt_{len(self._events) + 1}"

        event = {
            "id": event_id,
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._events.append(event)

        return event_id

    def get(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve event by ID (read-only access).
        """

        for event in self._events:
            if event["id"] == event_id:
                return event

        return None

    def query_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """
        Filter events by type (no interpretation).
        """

        return [
            event
            for event in self._events
            if event["type"] == event_type
        ]

    def all(self) -> List[Dict[str, Any]]:
        """
        Return full immutable log snapshot.
        """
        return list(self._events)