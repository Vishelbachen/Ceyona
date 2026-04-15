import datetime


class AnalyticsService:
    def __init__(self, db):
        self.db = db

    def log_event(self, user_id: str, event: str, meta: dict = None):
        data = {
            "user_id": user_id,
            "event": event,
            "meta": meta or {},
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        return self.db.insert("analytics", data)

    def get_user_stats(self, user_id: str):
        result = self.db.select(
            "analytics",
            filters={"user_id": user_id},
            limit=100
        )

        events = result.data if result else []

        return {
            "total_events": len(events),
            "last_event": events[-1] if events else None
        }