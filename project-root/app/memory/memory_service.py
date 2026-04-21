from typing import List, Dict, Any
import logging

from app.memory.session_store import SessionStore

logger = logging.getLogger("memory_service")


class MemoryService:
    """
    Cognitive memory layer (v4.1 production safe)

    Features:
    - cycle-safe (no core dependency)
    - structured context
    - stable trimming
    - LLM-safe size control
    """

    MAX_MESSAGES = 12
    MAX_TOTAL_CHARS = 6000
    MAX_MESSAGE_CHARS = 800

    def __init__(self, store: SessionStore):
        self.store = store

    # -------------------------
    # MAIN CONTEXT BUILDER
    # -------------------------
    def build_context(self, user_id: str) -> List[Dict[str, str]]:
        try:
            history = self.store.get_history(user_id)

            if not isinstance(history, list):
                return []

            trimmed = history[-self.MAX_MESSAGES:]

            result = []
            total_chars = 0

            for msg in trimmed:
                if not isinstance(msg, dict):
                    continue

                role = msg.get("role", "user")
                text = self._clean_text(msg.get("text"))

                if not text:
                    continue

                text = text[:self.MAX_MESSAGE_CHARS]

                size = len(text) + len(role)

                if total_chars + size > self.MAX_TOTAL_CHARS:
                    break

                result.append({
                    "role": role,
                    "text": text
                })

                total_chars += size

            return result

        except Exception as e:
            logger.exception(f"memory_build_failed: {e}")
            return []

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

    # -------------------------
    # FUTURE HOOKS
    # -------------------------
    def extract_facts(self, user_id: str) -> List[str]:
        return []

    def build_summary(self, user_id: str) -> str:
        return ""