from __future__ import annotations

from typing import List, Dict, Any, Optional
import time


# =========================
# CONVERSATION HISTORY
# =========================
class ConversationHistory:
    """
    ROLE:
    - store ordered conversation messages
    - provide recent dialogue context

    STRICT RULES:
    - no business logic
    - no summarization
    - no filtering by meaning
    - no token optimization
    """

    def __init__(self, max_messages: int = 50):
        self._messages: List[Dict[str, Any]] = []
        self._max_messages = max_messages

    # =========================
    # ADD MESSAGE
    # =========================
    def add(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:

        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }

        self._messages.append(message)

        # simple truncation (FIFO)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    # =========================
    # GET ALL
    # =========================
    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._messages)

    # =========================
    # GET LAST N
    # =========================
    def get_last(self, n: int) -> List[Dict[str, Any]]:
        if n <= 0:
            return []
        return self._messages[-n:]

    # =========================
    # CLEAR
    # =========================
    def clear(self) -> None:
        self._messages.clear()

    # =========================
    # SIZE
    # =========================
    def size(self) -> int:
        return len(self._messages)