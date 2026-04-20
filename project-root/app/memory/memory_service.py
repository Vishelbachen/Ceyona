from app.memory.session_store import SessionStore


class MemoryService:
    """
    Cognitive memory layer (v2-ready)

    Supports:
    - short-term chat history
    - structured context building
    - future long-term memory extension
    """

    def __init__(self, store: SessionStore):
        self.store = store

    # -------------------------
    # MAIN CONTEXT BUILDER
    # -------------------------
    def build_context(self, user_id: str) -> list[str]:
        """
        Returns LLM-ready context.
        """

        try:
            history = self.store.get_history(user_id)

            if not history:
                return []

            context = []

            # 🧠 last messages window (important fix)
            recent = history[-12:]  # prevents prompt bloat

            for msg in recent:
                role = msg.get("role", "unknown")
                text = (msg.get("text") or "").strip()

                if not text:
                    continue

                # clean formatting
                context.append(f"{role.upper()}: {text}")

            return context

        except Exception:
            # memory must NEVER break pipeline
            return []


    # -------------------------
    # FUTURE: STRUCTURED MEMORY HOOK
    # -------------------------
    def extract_facts(self, user_id: str) -> list[str]:
        """
        Placeholder for cognition layer.

        Will later store:
        - user preferences
        - stable facts
        - long-term memory
        """

        return []


    # -------------------------
    # FUTURE: MEMORY SUMMARY HOOK
    # -------------------------
    def build_summary(self, user_id: str) -> str:
        """
        Placeholder for summarization layer.
        """

        return ""