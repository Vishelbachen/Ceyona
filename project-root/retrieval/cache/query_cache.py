import hashlib
import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import ACTIVE_TTL

logger = logging.getLogger(__name__)


def _key(query: str, user_id: str) -> str:
    h = hashlib.sha256(f"{user_id}:{query}".encode()).hexdigest()
    return f"qcache:{h}"


class QueryCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, query: str, user_id: str) -> list[dict] | None:
        try:
            val = await self._redis.get(_key(query, user_id))
            return json.loads(val) if val else None
        except Exception as exc:
            logger.warning("QueryCache get failed", extra={"error": str(exc)})
            return None

    async def set(self, query: str, user_id: str, results: list[dict]) -> None:
        try:
            await self._redis.setex(
                _key(query, user_id),
                ACTIVE_TTL.query_ttl_seconds,
                json.dumps(results),
            )
        except Exception as exc:
            logger.warning("QueryCache set failed", extra={"error": str(exc)})