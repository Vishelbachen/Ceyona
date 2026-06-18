import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import RERANK_CACHE_TTL

logger = logging.getLogger(__name__)


class RerankCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, query: str, candidates_hash: str) -> str:
        return f"rerank:{query[:40]}:{candidates_hash[:12]}"

    async def get(self, query: str, candidates: list[str]) -> list[tuple[str, float]] | None:
        import hashlib
        h = hashlib.sha256("|".join(candidates).encode()).hexdigest()
        try:
            raw = await self._redis.get(self._key(query, h))
            if not raw:
                return None
            data = json.loads(raw)
            return [(d["content"], d["score"]) for d in data]
        except Exception as exc:
            logger.warning("RerankCache.get failed", extra={"error": str(exc)})
            return None

    async def set(self, query: str, candidates: list[str], results: list[tuple[str, float]]) -> None:
        import hashlib
        h = hashlib.sha256("|".join(candidates).encode()).hexdigest()
        try:
            data = [{"content": c, "score": s} for c, s in results]
            await self._redis.setex(
                self._key(query, h),
                RERANK_CACHE_TTL,
                json.dumps(data),
            )
        except Exception as exc:
            logger.warning("RerankCache.set failed", extra={"error": str(exc)})