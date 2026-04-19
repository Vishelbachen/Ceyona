from app.memory.session_store import SessionStore


class MemoryService:
    def __init__(self, store: SessionStore):
        self.store = store

    def build_context(self, user_id: str) -> list:
        return self.store.get_context(user_id)