from typing import Any, Dict, List, Optional
from datetime import datetime


class ConversationHistory:
    """
    AI Platform v4.7 — Conversation History Store

    RESPONSIBILITY:
    - Store raw chat messages
    - Provide chronological access to dialogue history
    - Serve as passive context source

    STRICT RULES:
    - No semantic interpretation
    - No summarization logic
    - No LLM usage
    - No retrieval decisions
    - No memory reasoning
    """

    def __init__(self):
        # in-memory fallback store (replace with DB in production)
        self._messages: List[Dict[str, Any]] = []

    def add_message(
        self,
        user_id: str,
        role: str,
        text: str,
    ) -> str:
        """
        Stores a single conversation message.
        """

        message_id = f"msg_{len(self._messages) + 1}"

        entry = {
            "id": message_id,
            "user_id": user_id,
            "role": role,  # user | assistant | system
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._messages.append(entry)

        return message_id

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns full conversation history for a user.
        """

        return [
            msg
            for msg in self._messages
            if msg["user_id"] == user_id
        ]

    def get_last_n(self, user_id: str, n: int = 10) -> List[Dict[str, Any]]:
        """
        Returns last N messages for context windowing.
        """

        history = self.get_history(user_id)

        return history[-n:]

    def clear(self, user_id: str) -> None:
        """
        Clears conversation history for a user.
        """

        self._messages = [
            msg
            for msg in self._messages
            if msg["user_id"] != user_id
        ]