import requests
from typing import Dict, Any


class TONPayments:
    def __init__(self, settings):
        self.wallet = settings.TON_WALLET

    def create_payment_link(self, user_id: str, amount: float) -> str:
        """
        Generates payment link (frontend/telegram redirect)
        """
        return f"https://ton.org/pay?to={self.wallet}&amount={amount}&user={user_id}"

    def verify_mock(self, tx_hash: str) -> Dict[str, Any]:
        """
        Placeholder for real blockchain verification
        (later replace with TON API / indexer)
        """
        return {
            "tx_hash": tx_hash,
            "status": "pending"
        }