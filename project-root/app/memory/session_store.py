from collections import defaultdict
from datetime import datetime


class SessionStore:
    """
    In-memory session storage (MVP safe + future-ready).
    """

    def __init__(self):
        self._data = defaultdict(list)

    def append_message(self, user_id: str, role: str, text: str):
        """
        Stores message with metadata (future-proof structure).
        """

        self._data[user_id].append({
            "role": role,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_history(self, user_id: str, limit: int = 20):
        """
        Returns last N messages (prevents memory growth explosion).
        """

        history = self._data.get(user_id, [])

        # safety: limit memory growth
        return history[-limit:]