async def get_balance(wallet: str):

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{TON_API}/getAddressBalance",
                params={"address": wallet}
            )

        if r.status_code != 200:
            return 0.0

        data = r.json()

        return int(data.get("result", 0)) / 1e9

    except Exception:
        return 0.0