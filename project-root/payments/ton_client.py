from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from infra.config_loader import ConfigLoader


class TONClient:
    """
    Thin TON network client wrapper.

    ROLE:
    - interact with TON API / wallet backend
    - send transactions
    - fetch balances / status

    DOES NOT:
    - decide pricing logic
    - enforce access rules
    - handle subscription logic
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
    ):
        config = ConfigLoader.load()

        self.base_url = base_url or "https://toncenter.com/api/v2"
        self.api_key = config.ton_wallet  # assumes wallet/API binding key or proxy token
        self.timeout = timeout

        self.client = httpx.AsyncClient(timeout=self.timeout)

    # =========================
    # INTERNAL REQUEST WRAPPER
    # =========================
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        url = f"{self.base_url}/{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            json=json,
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    # =========================
    # WALLET METHODS
    # =========================
    async def get_balance(self, address: str) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "getAddressBalance",
            params={"address": address},
        )

    async def get_transactions(self, address: str, limit: int = 10) -> Dict[str, Any]:
        return await self._request(
            "GET",
            "getTransactions",
            params={
                "address": address,
                "limit": limit,
            },
        )

    # =========================
    # TRANSFER
    # =========================
    async def send_transaction(
        self,
        to_address: str,
        amount_nano: int,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:

        payload = {
            "to_address": to_address,
            "amount": amount_nano,
            "comment": comment,
        }

        return await self._request(
            "POST",
            "sendTransaction",
            json=payload,
        )

    # =========================
    # CLEANUP
    # =========================
    async def close(self) -> None:
        await self.client.aclose()