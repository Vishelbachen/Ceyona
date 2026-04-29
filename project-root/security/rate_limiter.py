import logging
import time

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 60
_DEFAULT_RPM = 30


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.
    Per-user, per-minute limit.
    """

    def __init__(self, redis: Redis, rpm: int = _DEFAULT_RPM) -> None:
        self._redis = redis
        self._rpm = rpm

    async def is_allowed(self, user_id: int) -> bool:
        key = f"rate:{user_id}"
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        try:
            pipe = self._redis.pipeline()
            # remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # count remaining
            pipe.zcard(key)
            # add current request
            pipe.zadd(key, {str(now): now})
            # set expiry
            pipe.expire(key, _WINDOW_SECONDS * 2)
            results = await pipe.execute()

            count = results[1]
            if count >= self._rpm:
                logger.warning("Rate limit exceeded", extra={"user_id": user_id, "count": count})
                return False
            return True

        except Exception as exc:
            logger.error("RateLimiter error", extra={"error": str(exc)})
            return True  # fail open — never block on Redis error


# Module-level singleton factory (instantiated in bootstrap with redis)
_instance: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter | None:
    return _instance


def init_rate_limiter(redis: Redis, rpm: int = _DEFAULT_RPM) -> RateLimiter:
    global _instance
    _instance = RateLimiter(redis, rpm)
    return _instance