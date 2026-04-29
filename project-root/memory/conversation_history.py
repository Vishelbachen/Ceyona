import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "conversation_history"
_DEFAULT_LIMIT = 20


@dataclass(frozen=True)
class ConversationTurn:
    role: str       # "user" | "assistant"
    content: str
    created_at: str


class ConversationHistory:
    """
    Stores and retrieves conversation turns per user.
    Returns history in LLM-ready format: list[dict] with role/content.
    Storage only. No summarization. No semantic operations.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def append(
        self,
        user_id: str,
        role: str,
        content: str,
    ) -> bool:
        """Append a single turn to conversation history."""
        try:
            self._db.table(_TABLE).insert({
                "user_id": user_id,
                "role": role,
                "content": content,
            }).execute()
            return True
        except Exception as exc:
            logger.error("append failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False

    async def get(
        self,
        user_id: str,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[dict]:
        """
        Fetch recent conversation turns for a user.
        Returns LLM-ready format: [{"role": ..., "content": ...}]
        Ordered oldest → newest for correct LLM context.
        """
        try:
            result = (
                self._db.table(_TABLE)
                .select("role, content, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data or []
            # reverse: oldest first for LLM context
            rows = list(reversed(rows))
            return [{"role": r["role"], "content": r["content"]} for r in rows]

        except Exception as exc:
            logger.error("get history failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return []

    async def clear(self, user_id: str) -> bool:
        """Delete all conversation history for a user."""
        try:
            self._db.table(_TABLE).delete().eq("user_id", user_id).execute()
            logger.info("History cleared", extra={"user_id": user_id})
            return True
        except Exception as exc:
            logger.error("clear failed", extra={"error": str(exc)})
            return False