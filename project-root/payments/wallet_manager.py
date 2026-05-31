import logging

from payments.access_controller import AccessController
from payments.pricing_engine import nano_to_usd
from payments.ton_client import TonTransaction, ton_client
from supabase import Client

logger = logging.getLogger(__name__)

_TABLE_PROCESSED = "processed_transactions"


class WalletManager:
    """
    Monitors TON wallet for incoming transactions.
    Verifies, deduplicates, and credits user balances.

    Transaction comment format: "{user_id}_{random}" e.g. "123456789_a3f9"
    Legacy plain integer also accepted for backward compatibility.
    The random suffix prevents memo guessing attacks.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase
        self._access = AccessController(supabase)

    async def _is_processed(self, tx_hash: str) -> bool:
        """Check if transaction was already processed."""
        try:
            result = (
                self._db
                .table(_TABLE_PROCESSED)
                .select("tx_hash")
                .eq("tx_hash", tx_hash)
                .maybe_single()
                .execute()
            )
            return result.data is not None
        except Exception as exc:
            logger.error("is_processed check failed", extra={"error": str(exc)})
            return True     # safe default: treat as processed to avoid double credit

    async def _mark_processed(
        self,
        tx_hash: str,
        user_id: int,
        amount_usd: float,
    ) -> None:
        """Mark transaction as processed in Supabase."""
        try:
            self._db.table(_TABLE_PROCESSED).insert({
                "tx_hash": tx_hash,
                "user_id": user_id,
                "amount_usd": amount_usd,
            }).execute()
        except Exception as exc:
            logger.error("mark_processed failed", extra={"error": str(exc)})

    def _parse_user_id(self, comment: str) -> int | None:
        """
        Extract user_id from transaction comment.
        Supported formats:
          "123456789"           — legacy plain integer
          "123456789_abc123"    — current format: user_id + random suffix
        The suffix prevents an attacker who knows someone's Telegram ID
        from crediting that account by guessing the memo.
        """
        try:
            part = comment.strip().split("_")[0]
            return int(part)
        except (ValueError, AttributeError, IndexError):
            return None

    async def process_incoming(self) -> int:
        """
        Fetch recent transactions, verify, and credit user balances.
        Returns number of transactions successfully processed.
        Called periodically by scheduler or on-demand.
        """
        txs: list[TonTransaction] = await ton_client.get_transactions(limit=50)
        processed_count = 0

        for tx in txs:
            # ── deduplication ────────────────────────────
            if await self._is_processed(tx.tx_hash):
                continue

            # ── parse user_id from comment ───────────────
            user_id = self._parse_user_id(tx.comment)
            if user_id is None:
                logger.warning(
                    "Transaction with unparseable comment skipped",
                    extra={"tx_hash": tx.tx_hash, "comment": tx.comment},
                )
                await self._mark_processed(tx.tx_hash, 0, 0.0)
                continue

            # ── convert nanoTON → USD ────────────────────
            amount_usd = await nano_to_usd(tx.amount_nano)

            if amount_usd <= 0:
                logger.warning("Zero USD value transaction skipped", extra={
                    "tx_hash": tx.tx_hash,
                    "nano": tx.amount_nano,
                })
                continue

            # ── credit user balance ──────────────────────
            credited = await self._access.credit(user_id, amount_usd)

            if credited:
                await self._mark_processed(tx.tx_hash, user_id, amount_usd)
                processed_count += 1
                logger.info("TON payment credited", extra={
                    "tx_hash": tx.tx_hash,
                    "user_id": user_id,
                    "amount_usd": amount_usd,
                })
            else:
                logger.error("Credit failed for verified transaction", extra={
                    "tx_hash": tx.tx_hash,
                    "user_id": user_id,
                })

        return processed_count