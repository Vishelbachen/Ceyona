class TonClient:
    """
    Minimal TON blockchain client wrapper (mock layer for now)
    """

    def get_balance(self, wallet: str) -> float:
        return 0.0

    def send_payment(self, from_wallet: str, to_wallet: str, amount: float) -> bool:
        print(f"[TON] send {amount} from {from_wallet} to {to_wallet}")
        return True