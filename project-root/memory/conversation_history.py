import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "conversation_his"   # matches Supabase table name shown in screenshot
_MAX_HISTORY = 20


@dataclass
class ConversationTurn:
    role: str        # "user" | "assistant"
    content: str


class ConversationHistory:
    """
    Stores and retrieves per-user conversation turns from Supabase.
    Storage only. No semantic logic.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def append(
        self,
        user_id: int,
        role: str,
        content: str,
    ) -> bool:
        try:
            self._db.table(_TABLE).insert({
                "user_id": str(user_id),
                "role": role,
                "content": content,
            }).execute()
            return True
        except Exception as exc:
            logger.error("ConversationHistory.append failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False

    async def get_history(
        self,
        user_id: int,
        limit: int = _MAX_HISTORY,
    ) -> list[dict]:
        """
        Returns list of {"role": ..., "content": ...} dicts
        ordered oldest-first, ready for LLM messages array.
        """
        try:
            result = (
                self._db.table(_TABLE)
                .select("role, content, created_at")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            rows = result.data or []
            # reverse to chronological order
            rows.reverse()
            return [{"role": r["role"], "content": r["content"]} for r in rows]
        except Exception as exc:
            logger.error("ConversationHistory.get_history failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return []

    async def clear(self, user_id: int) -> bool:
        try:
            self._db.table(_TABLE).delete().eq(
                "user_id", str(user_id)
            ).execute()
            return True
        except Exception as exc:
            logger.error("ConversationHistory.clear failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False