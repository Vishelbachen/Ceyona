from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict

from payments.ton_client import TONClient


# =========================
# WALLET STATE (CACHE ONLY)
# =========================
@dataclass
class WalletState:
    balance_ton: float = 0.0
    last_sync: float = 0.0


# =========================
# WALLET MANAGER
# =========================
class WalletManager:
    """
    ROLE:
    - cache wallet state per user
    - synchronize balance with TON blockchain via TONClient
    - provide unified wallet abstraction for upper layers

    STRICT RULES:
    - no pricing logic
    - no access control
    - no billing decisions
    - no cost interpretation
    """

    SYNC_TTL = 60  # seconds

    def __init__(self, ton_client: TONClient):
        self._ton = ton_client
        self._state: Dict[str, WalletState] = {}

    # =========================
    # INTERNAL
    # =========================
    def _get(self, user_id: str) -> WalletState:
        if user_id not in self._state:
            self._state[user_id] = WalletState()
        return self._state[user_id]

    def _needs_sync(self, state: WalletState) -> bool:
        return (time.time() - state.last_sync) >= self.SYNC_TTL

    # =========================
    # SYNC BALANCE
    # =========================
    async def sync_balance(self, user_id: str, wallet_address: str) -> float:
        state = self._get(user_id)

        if not self._needs_sync(state):
            return state.balance_ton

        response = await self._ton.get_balance(wallet_address)

        raw_balance = response.get("result", 0)
        balance_ton = float(raw_balance) / 1e9  # nanoTON → TON

        state.balance_ton = balance_ton
        state.last_sync = time.time()

        return balance_ton

    # =========================
    # READ CACHE ONLY
    # =========================
    def get_cached_balance(self, user_id: str) -> float:
        return self._get(user_id).balance_ton

    # =========================
    # AFFORDABILITY CHECK (NO DECISION AUTHORITY)
    # =========================
    def can_afford(self, user_id: str, cost_ton: float) -> bool:
        state = self._get(user_id)
        return state.balance_ton >= cost_ton

    # =========================
    # LOCAL UPDATE AFTER PAYMENT CONFIRMATION
    # =========================
    def deduct_local(self, user_id: str, cost_ton: float) -> None:
        state = self._get(user_id)
        state.balance_ton = max(0.0, state.balance_ton - cost_ton)