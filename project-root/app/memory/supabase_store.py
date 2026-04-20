from supabase import create_client
from app.config.settings import settings
from app.core.logger import logger


class SupabaseStore:
    """
    Lightweight DB bridge for cognition layer.
    """

    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            self.client = None
            return

        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

    def is_enabled(self) -> bool:
        return self.client is not None

    def insert_reflection(self, table: str, payload: dict):
        if not self.client:
            return

        try:
            self.client.table(table).insert(payload).execute()

        except Exception as e:
            logger.log(
                "ERROR",
                "supabase_insert_failed",
                error=str(e)
            )