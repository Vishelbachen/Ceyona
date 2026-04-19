# app/memory/store.py

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class MemoryItem:
    role: str
    content: str


class MemoryStore:
    """
    MVP in-memory storage.
    No persistence. No external dependencies.
    """

    def __init__(self):
        self._store: Dict[str, List[MemoryItem]] = defaultdict(list)

    def add(self, chat_id: str, role: str, content: str):
        self._store[chat_id].append(
            MemoryItem(role=role, content=content)
        )

    def get(self, chat_id: str, limit: int = 10) -> List[MemoryItem]:
        return self._store[chat_id][-limit:]

    def clear(self, chat_id: str):
        self._store.pop(chat_id, None)