import httpx
from payments.ton_client import get_balance
from payments.pricing_engine import estimate_cost

async def check_access(user_wallet: str, intent: dict):

    try:
        balance = await get_balance(user_wallet)
        cost = estimate_cost(intent)

        return balance >= cost

    except Exception:
        return True  # fail-open (важно для стабильности)