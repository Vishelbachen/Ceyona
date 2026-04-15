class PaymentVerifier:
    def __init__(self, db, ton):
        self.db = db
        self.ton = ton

    async def verify_and_activate(self, user_id: str, tx_hash: str, plan: str):
        """
        Full flow:
        1. verify transaction
        2. if valid → activate subscription
        """

        result = self.ton.verify_mock(tx_hash)

        if result["status"] != "confirmed":
            return {
                "status": "failed",
                "reason": "Transaction not confirmed"
            }

        self.db.insert("subscriptions", {
            "user_id": user_id,
            "plan": plan,
            "active": True
        })

        return {
            "status": "success",
            "access": "granted"
        }