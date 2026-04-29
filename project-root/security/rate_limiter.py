import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_WINDOW_SECONDS = 60
_DEFAULT_LIMIT = 30


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int = 0


class RateLimiter:
    """
    Sliding window rate limiter using Redis.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def check(
        self,
        user_id: int,
        limit: int = _DEFAULT_LIMIT,
    ) -> RateLimitResult:
        key = f"rate:{user_id}"
        now = int(time.time())
        window_start = now - _WINDOW_SECONDS

        try:
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, _WINDOW_SECONDS)
            results = await pipe.execute()

            count = results[1]
            if count >= limit:
                logger.warning("Rate limit exceeded", extra={"user_id": user_id})
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=_WINDOW_SECONDS,
                )
            return RateLimitResult(allowed=True, remaining=limit - count - 1)

        except Exception as exc:
            logger.error("Rate limiter error", extra={"error": str(exc)})
            return RateLimitResult(allowed=True, remaining=limit)