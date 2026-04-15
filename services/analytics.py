import datetime
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db):
        self.db = db

    def log_event(self, user_id: str, event: str, meta: dict = None):
        try:
            data = {
                "user_id": str(user_id),
                "event": event,
                "meta": meta or {},
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

            return self.db.insert("analytics", data)

        except Exception as e:
            logger.warning(f"[ANALYTICS FAIL] {e}")
            return None

    def get_user_stats(self, user_id: str):
        try:
            result = self.db.select(
                "analytics",
                filters={"user_id": str(user_id)},
                limit=100
            )

            events = getattr(result, "data", []) or []

            return {
                "total_events": len(events),
                "last_event": events[-1] if events else None
            }

        except Exception as e:
            logger.warning(f"[ANALYTICS READ FAIL] {e}")
            return {
                "total_events": 0,
                "last_event": None
            }