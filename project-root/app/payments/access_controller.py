from payments.ton_client import get_balance
from payments.pricing import estimate_cost

def check_access(user_id: str, intent: dict) -> bool:

    balance = get_balance(user_id)
    cost = estimate_cost(intent)

    return balance >= cost