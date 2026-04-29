import logging

logger = logging.getLogger(__name__)


async def check_redis(redis) -> bool:
    try:
        await redis.ping()
        return True
    except Exception as exc:
        logger.warning("Redis healthcheck failed", extra={"error": str(exc)})
        return False


async def check_supabase(supabase) -> bool:
    try:
        supabase.table("user_balances").select("user_id").limit(1).execute()
        return True
    except Exception as exc:
        logger.warning("Supabase healthcheck failed", extra={"error": str(exc)})
        return False


async def full_health(app_state) -> dict:
    redis_ok = await check_redis(app_state.redis)
    supabase_ok = await check_supabase(app_state.supabase)
    healthy = redis_ok and supabase_ok
    return {
        "status": "ok" if healthy else "degraded",
        "redis": "ok" if redis_ok else "error",
        "supabase": "ok" if supabase_ok else "error",
    }