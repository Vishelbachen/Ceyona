from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Literal


# =========================
# PLAN DEFINITIONS
# =========================
PlanType = Literal["free", "pro", "premium"]


@dataclass
class PlanLimits:
    """
    Hard business limits (billing layer)

    NOTE:
    This layer is NOT security.
    This layer is NOT rate limiting.

    It defines subscription economics.
    """

    daily_requests: int
    monthly_requests: int
    monthly_price_ton: float


# =========================
# DEFAULT PLAN CONFIG
# =========================
PLANS: Dict[PlanType, PlanLimits] = {
    "free": PlanLimits(
        daily_requests=50,
        monthly_requests=3000,
        monthly_price_ton=0.0,
    ),
    "pro": PlanLimits(
        daily_requests=200,
        monthly_requests=10000,
        monthly_price_ton=10.0,
    ),
    "premium": PlanLimits(
        daily_requests=1000,
        monthly_requests=50000,
        monthly_price_ton=25.0,
    ),
}


# =========================
# USAGE STATE
# =========================
@dataclass
class UsageState:
    daily_count: int = 0
    monthly_count: int = 0

    day_window_start: float = field(default_factory=lambda: time.time())
    month_window_start: float = field(default_factory=lambda: time.time())


# =========================
# ACCESS DECISION
# =========================
@dataclass
class AccessDecision:
    allowed: bool
    reason: str = "ok"
    remaining_daily: Optional[int] = None
    remaining_monthly: Optional[int] = None


# =========================
# ACCESS CONTROLLER (BILLING LAYER)
# =========================
class AccessController:
    """
    ROLE:
    - enforce subscription limits (daily/monthly caps)
    - enforce plan-based access control
    - separate from security rate limiting

    DOES NOT:
    - handle burst protection (RateLimiter does that)
    - affect model routing (LLM layer does that)
    - affect retrieval or cognition
    """

    def __init__(self):
        self._usage: Dict[str, UsageState] = {}

    # =========================
    # INTERNAL HELPERS
    # =========================
    def _get_state(self, user_id: str) -> UsageState:
        if user_id not in self._usage:
            self._usage[user_id] = UsageState()
        return self._usage[user_id]

    def _reset_daily_if_needed(self, state: UsageState) -> None:
        now = time.time()
        if now - state.day_window_start >= 86400:  # 24h
            state.daily_count = 0
            state.day_window_start = now

    def _reset_monthly_if_needed(self, state: UsageState) -> None:
        now = time.time()
        if now - state.month_window_start >= 2592000:  # ~30 days
            state.monthly_count = 0
            state.month_window_start = now

    # =========================
    # MAIN ACCESS CHECK
    # =========================
    def check(
        self,
        user_id: str,
        plan: PlanType = "free",
    ) -> AccessDecision:

        limits = PLANS[plan]
        state = self._get_state(user_id)

        self._reset_daily_if_needed(state)
        self._reset_monthly_if_needed(state)

        # remaining calculation
        remaining_daily = limits.daily_requests - state.daily_count
        remaining_monthly = limits.monthly_requests - state.monthly_count

        # hard deny conditions
        if state.daily_count >= limits.daily_requests:
            return AccessDecision(
                allowed=False,
                reason="daily_limit_exceeded",
                remaining_daily=0,
                remaining_monthly=max(0, remaining_monthly),
            )

        if state.monthly_count >= limits.monthly_requests:
            return AccessDecision(
                allowed=False,
                reason="monthly_limit_exceeded",
                remaining_daily=max(0, remaining_daily),
                remaining_monthly=0,
            )

        return AccessDecision(
            allowed=True,
            remaining_daily=remaining_daily,
            remaining_monthly=remaining_monthly,
        )

    # =========================
    # COMMIT USAGE (CALL AFTER SUCCESSFUL REQUEST)
    # =========================
    def commit(
        self,
        user_id: str,
    ) -> None:
        state = self._get_state(user_id)

        self._reset_daily_if_needed(state)
        self._reset_monthly_if_needed(state)

        state.daily_count += 1
        state.monthly_count += 1

    # =========================
    # ADMIN RESET
    # =========================
    def reset(self, user_id: str) -> None:
        if user_id in self._usage:
            del self._usage[user_id]