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

        try:
            history = self.store.get_history(user_id)

            if not history:
                return []

            context = []

            for msg in history:
                role = msg.get("role", "unknown")
                text = msg.get("text", "")

                if not text:
                    continue

                context.append(f"{role}: {text}")

            return context

        except Exception:
            # memory NEVER breaks system
            return []