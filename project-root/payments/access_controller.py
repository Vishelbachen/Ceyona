from payments.ton_client import get_balance
from payments.pricing_engine import estimate_cost

async def check_access(user_wallet: str, intent: dict):

    balance = await get_balance(user_wallet)
    cost = estimate_cost(intent)

    return balance >= cost