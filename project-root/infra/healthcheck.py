import asyncio
import logging

from redis.asyncio import Redis
from supabase import Client

logger = logging.getLogger(__name__)

# Fly.io healthcheck timeout = 5s (fly.toml).
# Each sub-check must complete well within that window.
# Redis: typically <5ms. Supabase (sync client via to_thread): can be slow on cold start.
# Budget: 3s per check → total worst case ~6s, but checks run concurrently → actual ~3s.
_REDIS_TIMEOUT    = 3.0   # seconds
_SUPABASE_TIMEOUT = 3.0   # seconds


async def check_redis(redis: Redis) -> bool:
    try:
        await asyncio.wait_for(redis.ping(), timeout=_REDIS_TIMEOUT)
        return True
    except asyncio.TimeoutError:
        logger.error("Redis healthcheck timed out", extra={"timeout": _REDIS_TIMEOUT})
        return False
    except Exception as exc:
        logger.error("Redis healthcheck failed", extra={"error": str(exc)})
        return False


async def check_supabase(supabase: Client) -> bool:
    try:
        # Supabase Python client is synchronous — run in thread to avoid blocking event loop.
        # asyncio.wait_for wraps the coroutine with a deadline so fly.io /health never hangs.
        await asyncio.wait_for(
            asyncio.to_thread(
                lambda: supabase.table("user_balances").select("user_id").limit(1).execute()
            ),
            timeout=_SUPABASE_TIMEOUT,
        )
        return True
    except asyncio.TimeoutError:
        logger.error("Supabase healthcheck timed out", extra={"timeout": _SUPABASE_TIMEOUT})
        return False
    except Exception as exc:
        logger.error("Supabase healthcheck failed", extra={"error": str(exc)})
        return False


async def full_health(redis: Redis, supabase: Client) -> dict:
    # Run both checks concurrently — total latency = max(redis, supabase), not sum.
    redis_ok, sb_ok = await asyncio.gather(
        check_redis(redis),
        check_supabase(supabase),
    )
    from observability.metrics import snapshot as metrics_snapshot
    return {
        "redis":    "ok" if redis_ok else "error",
        "supabase": "ok" if sb_ok   else "error",
        "status":   "ok" if (redis_ok and sb_ok) else "degraded",
        "metrics":  metrics_snapshot(),
    }
