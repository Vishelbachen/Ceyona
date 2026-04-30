import logging
from dataclasses import dataclass

from supabase import Client

logger = logging.getLogger(__name__)

_TABLE = "user_balances"
_DEFAULT_BALANCE_USD = 1.0


@dataclass(frozen=True)
class BalanceResult:
    user_id: int
    balance_usd: float
    exists: bool


class AccessController:
    def __init__(self, supabase: Client) -> None:
        self._db = supabase

    async def get_balance(self, user_id: int) -> BalanceResult:
        try:
            # используем limit(1) вместо maybe_single() — избегаем 406
            result = (
                self._db.table(_TABLE)
                .select("balance_usd")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return BalanceResult(
                    user_id=user_id,
                    balance_usd=float(rows[0]["balance_usd"]),
                    exists=True,
                )
            # новый пользователь
            await self._create_default(user_id)
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

    async def _create_default(self, user_id: int) -> None:
        try:
            self._db.table(_TABLE).insert({
                "user_id": user_id,
                "balance_usd": _DEFAULT_BALANCE_USD,
            }).execute()
            logger.info("Default balance created", extra={
                "user_id": user_id,
                "balance_usd": _DEFAULT_BALANCE_USD,
            })
        except Exception as exc:
            logger.warning("Default balance creation failed", extra={
                "user_id": user_id,
                "error": str(exc),
            })

    async def credit(self, user_id: int, amount_usd: float) -> bool:
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
                "user_id": user_id, "error": str(exc),
            })
            return False

    async def deduct(self, user_id: int, amount_usd: float) -> bool:
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
                "user_id": user_id, "error": str(exc),
            })
            return False