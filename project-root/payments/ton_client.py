from __future__ import annotations

from typing import Any, Dict

import httpx


# =========================
# TON CLIENT
# =========================
class TONClient:
    """
    ROLE:
    - thin wrapper over TON API
    - fetch wallet data (balance, transactions if needed)
    - provide raw network responses

    STRICT RULES:
    - no business logic
    - no pricing logic
    - no access decisions
    - no caching policy (handled by WalletManager)
    """

    def __init__(self, base_url: str = "https://toncenter.com/api/v2", api_key: str | None = None):
        self.base_url = base_url
        self.api_key = api_key

        self._client = httpx.AsyncClient(timeout=10.0)

    # =========================
    # INTERNAL REQUEST
    # =========================
    async def _get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:

        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{self.base_url}/{endpoint}"

        response = await self._client.get(url, params=params)
        response.raise_for_status()

        return response.json()

    # =========================
    # WALLET BALANCE
    # =========================
    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:

        return await self._get(
            "getAddressBalance",
            {"address": wallet_address},
        )

    # =========================
    # TRANSACTION HISTORY (OPTIONAL FUTURE USE)
    # =========================
    async def get_transactions(
        self,
        wallet_address: str,
        limit: int = 10,
    ) -> Dict[str, Any]:

        return await self._get(
            "getTransactions",
            {
                "address": wallet_address,
                "limit": limit,
            },
        )

    # =========================
    # CLEANUP
    # =========================
    async def close(self) -> None:
        await self._client.aclose()