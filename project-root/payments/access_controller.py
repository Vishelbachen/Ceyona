from payments.wallet_manager import WalletManager
from payments.pricing_engine import PricingEngine


class AccessController:
    """
    Controls execution permission based on balance
    """

    def __init__(self):
        self.wallets = WalletManager()
        self.pricing = PricingEngine()

    def can_execute(self, user_id: str, tokens: int) -> bool:
        cost = self.pricing.calculate_cost(tokens)
        balance = self.wallets.get_balance(user_id)
        return balance >= cost