from typing import Any, Dict, List, Optional

from events.event_store import EventStore


class EventReplay:
    """
    AI Platform v4.7 — Event Replay Engine

    RESPONSIBILITY:
    - Reconstruct event history from EventStore
    - Provide deterministic replay of system events
    - Support debugging and audit analysis

    STRICT RULES:
    - No business logic
    - No decision-making
    - No triggering side effects
    - No LLM / retrieval / memory access
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def replay_all(self) -> List[Dict[str, Any]]:
        """
        Returns full event history in original order.
        """

        return self.event_store.all()

    def replay_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """
        Returns filtered event stream by type.
        """

        return self.event_store.query_by_type(event_type)

    def replay_from(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Reconstructs event stream starting from a specific event.
        """

        all_events = self.event_store.all()

        start_index = None

        for i, event in enumerate(all_events):
            if event["id"] == event_id:
                start_index = i
                break

        if start_index is None:
            return []

        return all_events[start_index:]

    def find(self, predicate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Simple filter-based search over event log.

        NOTE:
        - No semantic interpretation
        - Only exact matching on fields
        """

        results = []

        for event in self.event_store.all():
            match = True

            for key, value in predicate.items():
                if event.get(key) != value:
                    match = False
                    break

            if match:
                results.append(event)

        return results