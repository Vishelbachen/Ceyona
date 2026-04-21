import asyncio
from supabase import create_client
from typing import Optional

from app.config.settings import settings
from app.core.logger import logger


class SupabaseStore:
    """
    Cognition DB bridge (production-safe v3.1)

    FIXES:
    - fully async-safe execution
    - no event loop blocking
    - retry via async sleep
    """

    def __init__(self):
        self.enabled = bool(
            settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY
        )

        self.client = None

        if self.enabled:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )

    # -------------------------
    # STATUS
    # -------------------------
    def is_enabled(self) -> bool:
        return self.client is not None

    # -------------------------
    # MAIN INSERT (ASYNC SAFE)
    # -------------------------
    async def insert_reflection(
        self,
        table: str,
        payload: dict,
        trace_id: Optional[str] = None
    ):
        if not self.client:
            logger.log("WARN", "supabase_disabled", trace_id=trace_id)
            return None

        max_retries = 3

        for attempt in range(max_retries):

            try:
                logger.log(
                    "INFO",
                    "supabase_insert_attempt",
                    trace_id=trace_id,
                    table=table,
                    attempt=attempt
                )

                result = await asyncio.wait_for(
                    self._insert(table, payload),
                    timeout=5
                )

                logger.log(
                    "INFO",
                    "supabase_insert_success",
                    trace_id=trace_id,
                    table=table
                )

                return result

            except Exception as e:

                logger.log(
                    "ERROR",
                    "supabase_insert_error",
                    trace_id=trace_id,
                    table=table,
                    attempt=attempt,
                    error=str(e)
                )

                if attempt == max_retries - 1:
                    logger.log(
                        "CRITICAL",
                        "supabase_insert_failed_final",
                        trace_id=trace_id,
                        table=table
                    )
                    return None

                # async safe retry delay
                await asyncio.sleep(0.3 * (attempt + 1))

    # -------------------------
    # INTERNAL INSERT
    # -------------------------
    async def _insert(self, table: str, payload: dict):
        return self.client.table(table).insert(payload).execute()