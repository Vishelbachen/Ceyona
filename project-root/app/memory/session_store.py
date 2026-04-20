from collections import defaultdict, deque
from datetime import datetime, timezone


class SessionStore:
    """
    In-memory session storage (MVP safe + cognition-ready).
    """

    def __init__(self, max_history: int = 50):
        self._data = defaultdict(lambda: deque(maxlen=max_history))
        self.max_history = max_history

    # -------------------------
    # WRITE
    # -------------------------
    def append_message(
        self,
        user_id: str,
        role: str,
        text: str,
        meta: dict | None = None
    ):
        """
        Stores message with structured metadata.
        """

        if not user_id:
            return

        self._data[user_id].append({
            "role": role or "unknown",
            "text": text or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": meta or {}
        })

    # -------------------------
    # READ
    # -------------------------
    def get_history(self, user_id: str, limit: int = 20):
        """
        Returns last N messages safely.
        """

        if not user_id:
            return []

        history = list(self._data.get(user_id, []))

        return history[-limit:]

    # -------------------------
    # CONTEXT BUILDER (IMPORTANT ADDITION)
    # -------------------------
    def build_structured_context(self, user_id: str, limit: int = 20):
        """
        Cognitive-ready context format.
        """

        history = self.get_history(user_id, limit)

        if not history:
            return []

        context = []

        for msg in history:
            role = msg.get("role", "unknown")
            text = msg.get("text", "")

            if not text:
                continue

            context.append({
                "role": role,
                "text": text,
                "timestamp": msg.get("timestamp"),
                "meta": msg.get("meta", {})
            })

        return context