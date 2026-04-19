# app/memory/session_store.py

from collections import defaultdict
from typing import List, Dict


class SessionStore:
    """
    Simple in-memory session storage (MVP v1).
    Key: user_id
    Value: list of messages
    """

    def __init__(self, max_history: int = 20):
        self.store: Dict[str, List[str]] = defaultdict(list)
        self.max_history = max_history

    def get(self, user_id: str) -> List[str]:
        return self.store.get(user_id, [])

    def append(self, user_id: str, message: str):
        history = self.store[user_id]
        history.append(message)

        # keep only last N messages
        if len(history) > self.max_history:
            self.store[user_id] = history[-self.max_history:]