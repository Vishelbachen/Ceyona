import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import EMBEDDING_CACHE_TTL

logger = logging.getLogger(__name__)


class EmbeddingCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, text: str, model: str) -> str:
        import hashlib
        h = hashlib.sha256(f"{model}:{text}".encode()).hexdigest()[:16]
        return f"emb:{h}"

    async def get(self, text: str, model: str) -> list[float] | None:
        try:
            raw = await self._redis.get(self._key(text, model))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    async def set(self, text: str, model: str, vector: list[float]) -> None:
        try:
            await self._redis.setex(
                self._key(text, model),
                EMBEDDING_CACHE_TTL,
                json.dumps(vector),
            )
        except Exception as exc:
            logger.warning("EmbeddingCache.set failed", extra={"error": str(exc)})