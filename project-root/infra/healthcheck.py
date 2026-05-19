import logging

from redis.asyncio import Redis
from supabase import Client

logger = logging.getLogger(__name__)


async def check_redis(redis: Redis) -> bool:
    try:
        await redis.ping()
        return True
    except Exception as exc:
        logger.error("Redis healthcheck failed", extra={"error": str(exc)})
        return False


async def check_supabase(supabase: Client) -> bool:
    try:
        supabase.table("user_balances").select("user_id").limit(1).execute()
        return True
    except Exception as exc:
        logger.error("Supabase healthcheck failed", extra={"error": str(exc)})
        return False


async def full_health(redis: Redis, supabase: Client) -> dict:
    redis_ok = await check_redis(redis)
    sb_ok = await check_supabase(supabase)
    from observability.metrics import snapshot as metrics_snapshot
    return {
        "redis": "ok" if redis_ok else "error",
        "supabase": "ok" if sb_ok else "error",
        "status": "ok" if (redis_ok and sb_ok) else "degraded",
        "metrics": metrics_snapshot(),
    }