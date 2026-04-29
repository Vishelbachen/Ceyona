import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_DEFAULT_BALANCE_USD = 0.0
_TABLE = "user_balances"


@dataclass(frozen=True)
class BalanceResult:
    user_id: int
    balance_usd: float
    exists: bool


class AccessController:
    """
    Reads and writes user USD balances from Supabase.
    Single source of truth for user balance state.
    """

    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def get_balance(self, user_id: int) -> BalanceResult:
        """Fetch user balance. Returns 0.0 if user not found."""
        try:
            result = (
                self._db
                .table(_TABLE)
                .select("balance_usd")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if result.data:
                return BalanceResult(
                    user_id=user_id,
                    balance_usd=float(result.data["balance_usd"]),
                    exists=True,
                )
            return BalanceResult(
                user_id=user_id,
                balance_usd=_DEFAULT_BALANCE_USD,
                exists=False,
            )
        except Exception as exc:
            logger.error("get_balance failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return BalanceResult(
                user_id=user_id,
                balance_usd=_DEFAULT_BALANCE_USD,
                exists=False,
            )

    async def credit(self, user_id: int, amount_usd: float) -> bool:
        """
        Add USD credit to user balance (upsert).
        Called after verified TON payment.
        """
        try:
            existing = await self.get_balance(user_id)
            new_balance = existing.balance_usd + amount_usd

            self._db.table(_TABLE).upsert({
                "user_id": user_id,
                "balance_usd": new_balance,
            }).execute()

            logger.info("Balance credited", extra={
                "user_id": user_id,
                "amount_usd": amount_usd,
                "new_balance": new_balance,
            })
            return True

        except Exception as exc:
            logger.error("credit failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False

    async def deduct(self, user_id: int, amount_usd: float) -> bool:
        """
        Deduct USD from user balance after successful LLM execution.
        Returns False if insufficient balance.
        """
        try:
            existing = await self.get_balance(user_id)

            if existing.balance_usd < amount_usd:
                logger.warning("Insufficient balance for deduction", extra={
                    "user_id": user_id,
                    "balance": existing.balance_usd,
                    "required": amount_usd,
                })
                return False

            new_balance = existing.balance_usd - amount_usd

            self._db.table(_TABLE).update({
                "balance_usd": new_balance,
            }).eq("user_id", user_id).execute()

            logger.info("Balance deducted", extra={
                "user_id": user_id,
                "amount_usd": amount_usd,
                "new_balance": new_balance,
            })
            return True

        except Exception as exc:
            logger.error("deduct failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })
            return False