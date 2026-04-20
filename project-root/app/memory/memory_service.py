from typing import List

from app.memory.session_store import SessionStore
from app.core.logger import logger


class MemoryService:
    """
    Cognitive memory layer (v3)

    Features:
    - safe context building
    - prompt size control
    - text normalization
    - future-ready for long-term memory
    """

    # 🔒 limits (important for LLM stability)
    MAX_MESSAGES = 12
    MAX_TOTAL_CHARS = 6000
    MAX_MESSAGE_CHARS = 800

    def __init__(self, store: SessionStore):
        self.store = store

    # -------------------------
    # MAIN CONTEXT BUILDER
    # -------------------------
    def build_context(self, user_id: str) -> List[str]:
        """
        Returns LLM-ready context.
        Safe, trimmed, normalized.
        """

        try:
            history = self.store.get_history(user_id)

            if not history:
                return []

            context = []
            total_chars = 0

            # 🧠 last N messages
            recent = history[-self.MAX_MESSAGES:]

            for msg in recent:
                role = msg.get("role", "user")
                text = self._clean_text(msg.get("text"))

                if not text:
                    continue

                # 🔒 limit per message
                text = text[:self.MAX_MESSAGE_CHARS]

                formatted = f"{role.upper()}: {text}"

                total_chars += len(formatted)

                # 🔒 global limit
                if total_chars > self.MAX_TOTAL_CHARS:
                    break

                context.append(formatted)

            return context

        except Exception as e:
            logger.log(
                "ERROR",
                "memory_build_failed",
                error=str(e)
            )
            return []

    # -------------------------
    # CLEAN TEXT
    # -------------------------
    def _clean_text(self, text: str | None) -> str:
        if not text:
            return ""

        return (
            text.strip()
            .replace("\n\n", "\n")
            .replace("\r", "")
        )

    # -------------------------
    # FUTURE: FACT EXTRACTION
    # -------------------------
    def extract_facts(self, user_id: str) -> List[str]:
        """
        Future:
        - user preferences
        - stable knowledge
        """
        return []

    # -------------------------
    # FUTURE: SUMMARY
    # -------------------------
    def build_summary(self, user_id: str) -> str:
        """
        Future summarization layer.
        """
        return ""