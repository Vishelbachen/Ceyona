import hashlib
import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import ACTIVE_TTL

logger = logging.getLogger(__name__)


def _key(query: str, candidates: list[str]) -> str:
    raw = query + "|".join(candidates)
    h = hashlib.sha256(raw.encode()).hexdigest()
    return f"rerank:{h}"


class RerankCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, query: str, candidates: list[str]) -> list[float] | None:
        try:
            val = await self._redis.get(_key(query, candidates))
            return json.loads(val) if val else None
        except Exception as exc:
            logger.warning("RerankCache get failed", extra={"error": str(exc)})
            return None

    async def set(self, query: str, candidates: list[str], scores: list[float]) -> None:
        try:
            await self._redis.setex(
                _key(query, candidates),
                ACTIVE_TTL.rerank_ttl_seconds,
                json.dumps(scores),
            )
        except Exception as exc:
            logger.warning("RerankCache set failed", extra={"error": str(exc)})