import hashlib
import json
import logging

from redis.asyncio import Redis
from retrieval.cache.ttl_policy import ACTIVE_TTL

logger = logging.getLogger(__name__)


def _key(text: str, model: str) -> str:
    h = hashlib.sha256(f"{model}:{text}".encode()).hexdigest()
    return f"emb:{h}"


class EmbeddingCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, text: str, model: str) -> list[float] | None:
        try:
            val = await self._redis.get(_key(text, model))
            return json.loads(val) if val else None
        except Exception as exc:
            logger.warning("EmbeddingCache get failed", extra={"error": str(exc)})
            return None

    async def set(self, text: str, model: str, embedding: list[float]) -> None:
        try:
            await self._redis.setex(
                _key(text, model),
                ACTIVE_TTL.embedding_ttl_seconds,
                json.dumps(embedding),
            )
        except Exception as exc:
            logger.warning("EmbeddingCache set failed", extra={"error": str(exc)})