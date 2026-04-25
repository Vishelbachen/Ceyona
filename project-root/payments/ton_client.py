import httpx

TON_API = "https://toncenter.com/api/v2"

async def get_balance(wallet: str):

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{TON_API}/getAddressBalance",
            params={"address": wallet}
        )

    data = r.json()

    return int(data.get("result", 0)) / 1e9