import httpx

TON_API = "https://toncenter.com/api/v2"

async def get_balance(wallet: str):

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{TON_API}/getAddressBalance",
                params={"address": wallet}
            )

        data = r.json()
        return int(data.get("result", 0)) / 1e9

    except Exception:
        return 0.0  # fail-safe