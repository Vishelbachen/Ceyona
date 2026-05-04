from __future__ import annotations

import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "conversation_history"
_MAX_HISTORY = 20

# Safe token budget for history — leaves room for system prompt + user message + output
# llama-3.1-8b-instant TPM: 6000
# 512 output + 800 system prompt + 300 user message + 500 buffer = 2012
# history budget: 6000 - 2012 = ~3500, берём с запасом
_MAX_HISTORY_TOKENS = 2000


@dataclass
class ConversationTurn:
    role: str
    content: str


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _trim_history_to_budget(
    turns: list[dict],
    token_budget: int = _MAX_HISTORY_TOKENS,
) -> list[dict]:
    """
    Trim history from the oldest end to fit within token budget.
    Always keeps the most recent turns.
    """
    total = sum(_estimate_tokens(t["content"]) for t in turns)
    if total <= token_budget:
        return turns

    # Drop oldest turns until we fit
    while turns and total > token_budget:
        dropped = turns.pop(0)
        total -= _estimate_tokens(dropped["content"])

    return turns


class ConversationHistory:
    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def append(self, user_id: int, role: str, content: str) -> bool:
        try:
            self._db.table(_TABLE).insert({
                "user_id": str(user_id),
                "role": role,
                "content": content,
            }).execute()
            return True
        except Exception as exc:
            logger.error("ConversationHistory.append failed", extra={
                "user_id": user_id, "error": str(exc),
            })
            return False

    async def get_history(
        self,
        user_id: int,
        limit: int = _MAX_HISTORY,
    ) -> list[dict]:
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
            rows.reverse()
            turns = [{"role": r["role"], "content": r["content"]} for r in rows]
            trimmed = _trim_history_to_budget(turns)
            if len(trimmed) < len(turns):
                logger.info("History trimmed", extra={
                    "user_id": user_id,
                    "original": len(turns),
                    "trimmed": len(trimmed),
                })
            return trimmed
        except Exception as exc:
            logger.error("ConversationHistory.get_history failed", extra={
                "user_id": user_id, "error": str(exc),
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
                "user_id": user_id, "error": str(exc),
            })
            return False