class AccessControl:
    def __init__(self, db):
        self.db = db

    def is_premium(self, user_id: str) -> bool:
        result = self.db.select(
            "subscriptions",
            filters={"user_id": user_id}
        )

        data = result.data if result else []
        return any(item.get("active") for item in data)

    def require_access(self, user_id: str):
        if not self.is_premium(user_id):
            return False, "Access denied: subscription required"
        return True, "Access granted"