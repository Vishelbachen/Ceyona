from __future__ import annotations

import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "conversation_history"

# SQL fetch limit — upper bound only, token budget trims below this.
# 40 turns × ~280 tokens/turn ≈ 11 200 tokens — well above any budget.
# Previously was 20 turns and acted as a hard cap independent of tokens.
_MAX_HISTORY_FETCH = 40

# Tier-dependent token budgets for conversation history.
#
# Budget calculation (FAST tier — llama-3.1-8b-instant, 6000 TPM):
#   system prompt total:  ~1300-1800 tokens
#   output cap (FAST):    ~1024 tokens
#   user message:         ~100-300 tokens
#   safety buffer:        300 tokens
#   ──────────────────────────────────────
#   available for history: 6000 - 1800 - 1024 - 300 - 300 = ~1200 tokens (conservative)
#   → raised to 1800: headroom for shorter system prompts and brief messages
#
# Budget calculation (GENERAL / HEAVY tier — llama-3.3-70b-versatile, 12 000 TPM):
#   system prompt total:  ~1300-1800 tokens
#   output cap (GENERAL): ~3072 tokens
#   user message:         ~100-300 tokens
#   safety buffer:        500 tokens
#   ──────────────────────────────────────────
#   available for history: 12000 - 1800 - 3072 - 300 - 500 = ~6328 tokens
#   → capped at 3500: keeps context meaningful without ballooning cost
#
# Tier is unknown at history load time (EPK runs after retrieval).
# Caller passes the appropriate budget based on complexity heuristic
# (same logic as orchestrator._estimate_tier): LOW + short → FAST_BUDGET,
# otherwise GENERAL_BUDGET.
FAST_HISTORY_BUDGET    = 2800   # ~10-11 pairs — raised from 1800 to reduce context loss on short messages
GENERAL_HISTORY_BUDGET = 3500   # ~12-15 pairs


@dataclass
class ConversationTurn:
    role: str
    content: str


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _trim_history_to_budget(
    turns: list[dict],
    token_budget: int,
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
        token_budget: int = GENERAL_HISTORY_BUDGET,
        limit: int = _MAX_HISTORY_FETCH,
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
            trimmed = _trim_history_to_budget(turns, token_budget)
            if len(trimmed) < len(turns):
                logger.info("History trimmed", extra={
                    "user_id":      user_id,
                    "original":     len(turns),
                    "trimmed":      len(trimmed),
                    "token_budget": token_budget,
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