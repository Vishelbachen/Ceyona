import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import QUERY_CACHE_TTL

logger = logging.getLogger(__name__)


class QueryCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, query: str, user_id: str) -> str:
        import hashlib
        h = hashlib.sha256(f"{user_id}:{query}".encode()).hexdigest()[:16]
        return f"qcache:{h}"

    async def get(self, query: str, user_id: str) -> list[dict] | None:
        try:
            raw = await self._redis.get(self._key(query, user_id))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, query: str, user_id: str, results: list[dict]) -> None:
        try:
            await self._redis.setex(
                self._key(query, user_id),
                QUERY_CACHE_TTL,
                json.dumps(results),
            )
        except Exception as exc:
            logger.warning("QueryCache.set failed", extra={"error": str(exc)})