import asyncio
from supabase import create_client
from typing import Optional

from app.config.settings import settings
from app.core.logger import logger


class SupabaseStore:
    """
    Cognition DB bridge (production-safe v3)

    Features:
    - retry logic
    - timeout protection
    - safe failure mode
    - structured logging
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
    # MAIN INSERT
    # -------------------------
    def insert_reflection(self, table: str, payload: dict, trace_id: Optional[str] = None):
        """
        Safe DB insert with retry + timeout.
        """

        if not self.client:
            logger.log(
                "WARN",
                "supabase_disabled",
                trace_id=trace_id
            )
            return

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

                # timeout wrapper (prevents hanging requests)
                result = asyncio.wait_for(
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

                await_sleep = 0.3 * (attempt + 1)
                asyncio.get_event_loop().run_until_complete(
                    asyncio.sleep(await_sleep)
                )

    # -------------------------
    # INTERNAL INSERT
    # -------------------------
    async def _insert(self, table: str, payload: dict):
        """
        Actual Supabase call wrapper.
        """

        return self.client.table(table).insert(payload).execute()