class WalletManager:
    """
    Manages internal user wallets (logical layer)
    """

    def __init__(self):
        self.wallets = {}

    def create_wallet(self, user_id: str):
        self.wallets[user_id] = 0.0

    def add_funds(self, user_id: str, amount: float):
        self.wallets[user_id] = self.wallets.get(user_id, 0.0) + amount

    def get_balance(self, user_id: str) -> float:
        return self.wallets.get(user_id, 0.0)