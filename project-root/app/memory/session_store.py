from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock

from app.core.logger import logger


class SessionStore:
    """
    In-memory session storage (production-ready v3)

    Features:
    - thread-safe
    - bounded memory
    - safe input handling
    - structured context support
    """

    MAX_TEXT_LENGTH = 2000

    def __init__(self, max_history: int = 50):
        self._data = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = Lock()
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
        Safe message append.
        """

        if not user_id:
            return

        text = self._clean_text(text)

        if not text:
            return

        entry = {
            "role": role or "unknown",
            "text": text[:self.MAX_TEXT_LENGTH],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": meta or {}
        }

        try:
            with self._lock:
                self._data[user_id].append(entry)

        except Exception as e:
            logger.log(
                "ERROR",
                "session_append_failed",
                user_id=user_id,
                error=str(e)
            )

    # -------------------------
    # READ
    # -------------------------
    def get_history(self, user_id: str, limit: int = 20):
        """
        Returns last N messages safely.
        """

        if not user_id:
            return []

        try:
            with self._lock:
                history = list(self._data.get(user_id, []))

            return history[-limit:]

        except Exception as e:
            logger.log(
                "ERROR",
                "session_read_failed",
                user_id=user_id,
                error=str(e)
            )
            return []

    # -------------------------
    # STRUCTURED CONTEXT
    # -------------------------
    def build_structured_context(self, user_id: str, limit: int = 20):
        """
        Cognitive-ready structured context.
        """

        history = self.get_history(user_id, limit)

        if not history:
            return []

        context = []
        total_chars = 0
        max_total = 6000

        for msg in history:
            role = msg.get("role", "unknown")
            text = self._clean_text(msg.get("text"))

            if not text:
                continue

            entry = {
                "role": role,
                "text": text[:1000],
                "timestamp": msg.get("timestamp"),
                "meta": msg.get("meta", {})
            }

            total_chars += len(entry["text"])

            if total_chars > max_total:
                break

            context.append(entry)

        return context

    # -------------------------
    # CLEAR SESSION
    # -------------------------
    def clear_session(self, user_id: str):
        """
        Removes user session from memory.
        """

        try:
            with self._lock:
                if user_id in self._data:
                    del self._data[user_id]

        except Exception as e:
            logger.log(
                "ERROR",
                "session_clear_failed",
                user_id=user_id,
                error=str(e)
            )

    # -------------------------
    # CLEAN TEXT
    # -------------------------
    def _clean_text(self, text: str | None) -> str:
        if not text:
            return ""

        return (
            text.strip()
            .replace("\r", "")
            .replace("\n\n", "\n")
        )