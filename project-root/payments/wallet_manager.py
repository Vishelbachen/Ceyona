from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from payments.ton_client import TONClient


# =========================
# WALLET STATE
# =========================
@dataclass
class WalletState:
    balance_ton: float = 0.0
    last_sync: float = 0.0


# =========================
# WALLET MANAGER (DOMAIN ORCHESTRATION FOR PAYMENTS)
# =========================
class WalletManager:
    """
    ROLE:
    - maintain cached wallet state
    - synchronize with TON network via TONClient
    - provide unified wallet abstraction for payments layer

    DOES NOT:
    - decide pricing
    - enforce access rules
    - calculate cost per request
    """

    SYNC_TTL = 60  # seconds

    def __init__(self, ton_client: TONClient):
        self.ton = ton_client
        self._state: Dict[str, WalletState] = {}

    # =========================
    # INTERNAL
    # =========================
    def _get(self, user_id: str) -> WalletState:
        if user_id not in self._state:
            self._state[user_id] = WalletState()
        return self._state[user_id]

    def _needs_sync(self, state: WalletState) -> bool:
        return (time.time() - state.last_sync) > self.SYNC_TTL

    # =========================
    # BALANCE SYNC
    # =========================
    async def sync_balance(self, user_id: str, wallet_address: str) -> float:
        state = self._get(user_id)

        if not self._needs_sync(state):
            return state.balance_ton

        response = await self.ton.get_balance(wallet_address)

        # TON API formats vary; assume raw balance in nanoTON
        raw_balance = response.get("result", 0)
        balance_ton = float(raw_balance) / 1e9

        state.balance_ton = balance_ton
        state.last_sync = time.time()

        return balance_ton

    # =========================
    # READ ONLY BALANCE
    # =========================
    def get_cached_balance(self, user_id: str) -> float:
        return self._get(user_id).balance_ton

    # =========================
    # PAYMENT RESERVE CHECK (NO DECISION AUTHORITY)
    # =========================
    def can_afford(self, user_id: str, cost_ton: float) -> bool:
        state = self._get(user_id)
        return state.balance_ton >= cost_ton

    # =========================
    # OPTIONAL RESERVE UPDATE (POST PAYMENT)
    # =========================
    def deduct_local(self, user_id: str, cost_ton: float) -> None:
        state = self._get(user_id)
        state.balance_ton = max(0.0, state.balance_ton - cost_ton)