"""
infra/redis_keys.py

Canonical Redis key registry for Ceyona.

Rules:
  - Every Redis key format lives here — one place to rename, one place to audit TTLs.
  - Any new Redis key must be added here first.
  - Existing keys are migrated here when their owning module is touched.
"""

# ── Low balance warning ────────────────────────────────────────────────────────

LOW_BALANCE_WARNING_TTL: int = 24 * 60 * 60  # seconds


def low_balance_warning(user_id: int) -> str:
    """
    Dedup flag: set with nx=True after sending a low-balance warning.
    Expires after LOW_BALANCE_WARNING_TTL. Deleted on BALANCE_CREDITED.
    """
    return f"low_balance_warned:{user_id}"