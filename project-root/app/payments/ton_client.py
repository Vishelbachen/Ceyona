import httpx
from app.settings import settings

TON_API = "https://toncenter.com/api/v2"

async def get_balance(wallet: str):

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{TON_API}/getAddressBalance",
            params={"address": wallet}
        )

    data = r.json()

    return int(data["result"]) / 1e9