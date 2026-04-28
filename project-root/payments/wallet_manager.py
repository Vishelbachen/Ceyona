from typing import Dict, Any, Optional


class WalletManager:
    """
    AI Platform v4.7 — Wallet Manager

    RESPONSIBILITY:
    - Store and retrieve user balances
    - Update balances after usage
    - Act as persistent financial state layer

    STRICT RULES:
    - No pricing calculations
    - No access control logic
    - No LLM / retrieval / memory usage
    - No decision-making authority
    """

    def __init__(self):
        # in-memory store (replace with DB in production)
        self._balances: Dict[str, float] = {}

    def get_balance(self, user_id: str) -> float:
        """
        Returns current user balance.
        """

        return self._balances.get(user_id, 0.0)

    def credit(self, user_id: str, amount: float) -> float:
        """
        Adds funds to user wallet.
        """

        current = self._balances.get(user_id, 0.0)
        updated = current + amount

        self._balances[user_id] = updated

        return updated

    def debit(self, user_id: str, amount: float) -> float:
        """
        Deducts funds from user wallet.
        """

        current = self._balances.get(user_id, 0.0)
        updated = current - amount

        self._balances[user_id] = updated

        return updated

    def set_balance(self, user_id: str, amount: float) -> None:
        """
        Direct balance override (admin/system only).
        """

        self._balances[user_id] = amount

    def exists(self, user_id: str) -> bool:
        """
        Checks if wallet exists.
        """

        return user_id in self._balances