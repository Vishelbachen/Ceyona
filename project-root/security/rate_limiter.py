import logging
import time

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_DEFAULT_RPM = 30
_WINDOW_SECONDS = 60


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis.
    Per-user, per-minute.
    """

    def __init__(self, redis: Redis, rpm: int = _DEFAULT_RPM) -> None:
        self._redis = redis
        self._rpm = rpm

    def _key(self, user_id: int) -> str:
        return f"rl:{user_id}"

    async def is_allowed(self, user_id: int) -> bool:
        key = self._key(user_id)
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, _WINDOW_SECONDS * 2)
            results = await pipe.execute()

            count = results[1]
            if count >= self._rpm:
                logger.warning("Rate limit exceeded", extra={"user_id": user_id, "count": count})
                return False
            return True

        except Exception as exc:
            logger.warning("RateLimiter error, allowing", extra={"error": str(exc)})
            return True  # fail open


_rate_limiter: RateLimiter | None = None


def get_rate_limiter(redis: Redis) -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(redis)
    return _rate_limiter