import logging
from dataclasses import dataclass

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)

_TONCENTER_BASE = "https://toncenter.com/api/v2"
_TIMEOUT = 15.0


@dataclass(frozen=True)
class TonTransaction:
    tx_hash: str
    from_address: str
    amount_nano: int        # in nanoTON (1 TON = 1_000_000_000 nanoTON)
    timestamp: int          # unix timestamp
    comment: str            # memo / user_id passed as comment


@dataclass(frozen=True)
class TonBalance:
    address: str
    balance_nano: int


class TonClient:
    """
    Toncenter API v2 client.
    Reads transactions and balance for the platform wallet.
    Read-only — no signing, no sending.
    """

    def __init__(self) -> None:
        self._wallet = settings.ton_wallet
        self._http = httpx.AsyncClient(
            base_url=_TONCENTER_BASE,
            timeout=_TIMEOUT,
        )

    async def get_transactions(
        self,
        limit: int = 50,
        lt: int | None = None,
        hash_: str | None = None,
    ) -> list[TonTransaction]:
        """
        Fetch recent incoming transactions for platform wallet.
        Supports pagination via lt + hash_ (logical time).
        """
        params: dict = {
            "address": self._wallet,
            "limit": limit,
            "archival": False,
        }
        if lt and hash_:
            params["lt"] = lt
            params["hash"] = hash_

        try:
            response = await self._http.get("/getTransactions", params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                logger.error("Toncenter error", extra={"response": data})
                return []

            txs = []
            for item in data.get("result", []):
                in_msg = item.get("in_msg", {})
                value = int(in_msg.get("value", 0))
                if value <= 0:
                    continue  # skip outgoing / system txs

                txs.append(TonTransaction(
                    tx_hash=item.get("transaction_id", {}).get("hash", ""),
                    from_address=in_msg.get("source", ""),
                    amount_nano=value,
                    timestamp=int(item.get("utime", 0)),
                    comment=in_msg.get("message", ""),
                ))

            return txs

        except Exception as exc:
            logger.error("get_transactions failed", extra={"error": str(exc)})
            return []

    async def get_balance(self) -> TonBalance:
        """Fetch current balance of platform wallet."""
        try:
            response = await self._http.get(
                "/getAddressBalance",
                params={"address": self._wallet},
            )
            response.raise_for_status()
            data = response.json()

            balance_nano = int(data.get("result", 0))
            return TonBalance(address=self._wallet, balance_nano=balance_nano)

        except Exception as exc:
            logger.error("get_balance failed", extra={"error": str(exc)})
            return TonBalance(address=self._wallet, balance_nano=0)

    async def aclose(self) -> None:
        await self._http.aclose()


# Singleton
ton_client = TonClient()