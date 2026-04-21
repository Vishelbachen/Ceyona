from typing import List, Dict, Any

from app.memory.session_store import SessionStore
from app.core.logger import logger


class MemoryService:
    """
    Cognitive memory layer (v4 PRODUCTION)

    Features:
    - structured context (no formatting leakage)
    - safe history validation
    - stable trimming strategy
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

            cleaned = []

            # 🧠 берем только последние сообщения
            for msg in history[-self.MAX_MESSAGES:]:

                if not isinstance(msg, dict):
                    continue

                role = msg.get("role", "user")
                text = self._clean_text(msg.get("text"))

                if not text:
                    continue

                text = text[:self.MAX_MESSAGE_CHARS]

                cleaned.append({
                    "role": role,
                    "text": text
                })

            # -------------------------
            # SAFE TRIM BY TOTAL SIZE
            # -------------------------
            result = []
            total_chars = 0

            for msg in reversed(cleaned):
                size = len(msg["text"]) + len(msg["role"])

                if total_chars + size > self.MAX_TOTAL_CHARS:
                    break

                result.append(msg)
                total_chars += size

            return list(reversed(result))

        except Exception as e:
            logger.log(
                "ERROR",
                "memory_build_failed",
                user_id=user_id,
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
            .replace("\r", "")
            .replace("\n\n", "\n")
        )

    # -------------------------
    # FUTURE: FACT EXTRACTION
    # -------------------------
    def extract_facts(self, user_id: str) -> List[str]:
        return []

    # -------------------------
    # FUTURE: SUMMARY
    # -------------------------
    def build_summary(self, user_id: str) -> str:
        return ""