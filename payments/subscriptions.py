import datetime


class Subscriptions:
    def __init__(self, db):
        self.db = db

    def create_subscription(self, user_id: str, plan: str):
        data = {
            "user_id": user_id,
            "plan": plan,
            "active": True,
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        return self.db.insert("subscriptions", data)

    def deactivate(self, user_id: str):
        return self.db.client.table("subscriptions") \
            .update({"active": False}) \
            .eq("user_id", user_id) \
            .execute()