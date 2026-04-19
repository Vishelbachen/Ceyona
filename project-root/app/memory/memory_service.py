from app.memory.session_store import SessionStore


class MemoryService:
    """
    Safe memory layer (non-blocking).
    """

    def __init__(self, store: SessionStore):
        self.store = store

    def build_context(self, user_id: str):
        try:
            return self.store.get_history(user_id)
        except Exception:
            return []

    def save(self, user_id: str, role: str, text: str):
        try:
            self.store.append_message(user_id, role, text)
        except Exception:
            # never break system
            pass