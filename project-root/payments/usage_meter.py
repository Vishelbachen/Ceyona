import logging
from dataclasses import dataclass

from payments.pricing_engine import apply_margin
from supabase import Client

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
    model: str                  # agent model (coordination.model — final executing model)
    resolved_model: str = ""    # preferred_model resolved by model_router before routing
                                # (models.md §25.3 — per-model billing readiness)
                                # Empty string when not available (e.g. DEGRADED_MODE).
    intent: str = ""
    lang: str = "en"
    # Speech billing (audio_seconds for ASR, tts_characters for TTS)
    audio_seconds: float = 0.0      # whisper billing: per hour transcribed
    tts_characters: int = 0         # orpheus billing: per 1M characters
    # Agent tool call billing (compound web_search: $5.00 / 1000 calls)
    tool_calls: int = 0


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
        """Write usage record to Supabase.

        Strategy: always write core fields. Extended speech/tool columns
        (audio_seconds, tts_characters, tool_calls) are included only when
        non-zero. If Supabase returns PGRST204 (column missing from schema
        cache), we retry with core fields only — billing stays alive while
        the DB migration is pending (architecture.md §27: speech billing
        NOT YET WIRED).

        Migration SQL to run in Supabase when speech billing is wired:
            ALTER TABLE usage_log
                ADD COLUMN IF NOT EXISTS audio_seconds   FLOAT8  NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tts_characters  BIGINT  NOT NULL DEFAULT 0,
                ADD COLUMN IF NOT EXISTS tool_calls      BIGINT  NOT NULL DEFAULT 0;
        """
        core_payload = {
            "user_id":          entry.user_id,
            "input_tokens":     entry.input_tokens,
            "output_tokens":    entry.output_tokens,
            "embedding_tokens": entry.embedding_tokens,
            "rerank_tokens":    entry.rerank_tokens,
            "tier":             entry.tier,
            "embedding_type":   entry.embedding_type,
            "raw_cost_usd":     entry.raw_cost_usd,
            "billed_cost_usd":  entry.billed_cost_usd,
            "model":            entry.model,
            "resolved_model":   entry.resolved_model,
            "intent":           entry.intent,
            "lang":             entry.lang,
        }

        # Include extended fields only when they carry actual data.
        # Zero values are omitted — avoids PGRST204 on missing columns.
        extended_payload: dict = {}
        if entry.audio_seconds:
            extended_payload["audio_seconds"] = entry.audio_seconds
        if entry.tts_characters:
            extended_payload["tts_characters"] = entry.tts_characters
        if entry.tool_calls:
            extended_payload["tool_calls"] = entry.tool_calls

        payload = {**core_payload, **extended_payload}

        try:
            self._db.table(_TABLE).insert(payload).execute()
            logger.info("Usage recorded", extra={
                "user_id":    entry.user_id,
                "billed_usd": entry.billed_cost_usd,
                "tier":       entry.tier,
            })
            return True

        except Exception as exc:
            error_str = str(exc)

            # PGRST204: extended column missing from schema cache.
            # Retry with core fields only — keeps billing alive until
            # migration runs. Log WARNING (not ERROR) so Sentry noise drops.
            if "PGRST204" in error_str and extended_payload:
                logger.warning(
                    "usage_log missing extended columns — retrying core-only. "
                    "Run migration: ALTER TABLE usage_log "
                    "ADD COLUMN IF NOT EXISTS audio_seconds FLOAT8 DEFAULT 0, "
                    "ADD COLUMN IF NOT EXISTS tts_characters BIGINT DEFAULT 0, "
                    "ADD COLUMN IF NOT EXISTS tool_calls BIGINT DEFAULT 0, "
                    "ADD COLUMN IF NOT EXISTS resolved_model TEXT DEFAULT ''.",
                    extra={"user_id": entry.user_id, "hint": error_str[:200]},
                )
                try:
                    self._db.table(_TABLE).insert(core_payload).execute()
                    logger.info("Usage recorded (core only — migration pending)", extra={
                        "user_id":    entry.user_id,
                        "billed_usd": entry.billed_cost_usd,
                        "tier":       entry.tier,
                    })
                    return True
                except Exception as exc2:
                    logger.error("usage record failed (core retry)", extra={
                        "user_id": entry.user_id,
                        "error":   str(exc2),
                    })
                    return False

            logger.error("usage record failed", extra={
                "user_id": entry.user_id,
                "error":   error_str,
            })
            return False