from typing import Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MemoryItem:
    role: str
    content: str


class MemoryStore:
    """
    Simple in-memory context storage (MVP stage).
    Keyed by chat_id.
    """

    def __init__(self):
        self._store: Dict[str, list[MemoryItem]] = defaultdict(list)

    def add(self, chat_id: str, role: str, content: str):
        self._store[chat_id].append(
            MemoryItem(role=role, content=content)
        )

    def get(self, chat_id: str, limit: int = 10) -> list[MemoryItem]:
        return self._store[chat_id][-limit:]

    def clear(self, chat_id: str):
        self._store.pop(chat_id, None)