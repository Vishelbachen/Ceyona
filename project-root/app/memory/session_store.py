from collections import defaultdict
from datetime import datetime, timezone


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

        if not user_id:
            return

        self._data[user_id].append({
            "role": role or "unknown",
            "text": text or "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_history(self, user_id: str, limit: int = 20):
        """
        Returns last N messages (prevents memory growth explosion).
        """

        if not user_id:
            return []

        history = self._data.get(user_id, [])

        return history[-limit:]