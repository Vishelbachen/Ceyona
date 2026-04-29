import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HealthStatus:
    ok: bool
    checks: dict[str, bool]


async def run_checks(redis=None, supabase=None) -> HealthStatus:
    checks: dict[str, bool] = {}

    # Redis
    if redis:
        try:
            await redis.ping()
            checks["redis"] = True
        except Exception as exc:
            logger.error("Redis health check failed", extra={"error": str(exc)})
            checks["redis"] = False
    else:
        checks["redis"] = False

    # Supabase
    if supabase:
        try:
            supabase.table("user_balances").select("user_id").limit(1).execute()
            checks["supabase"] = True
        except Exception as exc:
            logger.error("Supabase health check failed", extra={"error": str(exc)})
            checks["supabase"] = False
    else:
        checks["supabase"] = False

    return HealthStatus(ok=all(checks.values()), checks=checks)