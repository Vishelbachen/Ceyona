from app.memory.session_store import SessionStore


class MemoryService:
    """
    Memory abstraction layer.

    Purpose:
    - isolate orchestrator from storage implementation
    - allow future swap (Redis / DB / vector store)
    """

    def __init__(self, store: SessionStore):
        self.store = store

    def build_context(self, user_id: str) -> list[str]:
        """
        Converts raw memory into LLM-ready context.
        """

        history = self.store.get_history(user_id)

        if not history:
            return []

        # normalize format for prompt layer
        return [
            f"{msg['role']}: {msg['text']}"
            for msg in history
        ]