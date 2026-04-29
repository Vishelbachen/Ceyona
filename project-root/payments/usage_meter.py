import logging
from dataclasses import dataclass

from supabase import Client

from payments.pricing_engine import apply_margin

logger = logging.getLogger(__name__)

_TABLE = "usage_log"


@dataclass(frozen=True)
class UsageEntry:
    user_id: int
    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    rerank_tokens: int
    tier: str
    embedding_type: str
    raw_cost_usd: float
    billed_cost_usd: float      # with margin applied
    model: str
    intent: str = ""
    lang: str = "en"


class UsageMeter:
    """
    Records usage and computes billed cost with margin.
    Writes to Supabase usage_log table.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    def compute_billed(self, raw_cost_usd: float) -> float:
        """Apply platform margin to raw LLM cost."""
        return apply_margin(raw_cost_usd)

    async def record(self, entry: UsageEntry) -> bool:
        """Write usage record to Supabase."""
        try:
            self._db.table(_TABLE).insert({
                "user_id": entry.user_id,
                "input_tokens": entry.input_tokens,
                "output_tokens": entry.output_tokens,
                "embedding_tokens": entry.embedding_tokens,
                "rerank_tokens": entry.rerank_tokens,
                "tier": entry.tier,
                "embedding_type": entry.embedding_type,
                "raw_cost_usd": entry.raw_cost_usd,
                "billed_cost_usd": entry.billed_cost_usd,
                "model": entry.model,
                "intent": entry.intent,
                "lang": entry.lang,
            }).execute()

            logger.info("Usage recorded", extra={
                "user_id": entry.user_id,
                "billed_usd": entry.billed_cost_usd,
                "tier": entry.tier,
            })
            return True

        except Exception as exc:
            logger.error("usage record failed", extra={
                "user_id": entry.user_id,
                "error": str(exc),
            })
            return False