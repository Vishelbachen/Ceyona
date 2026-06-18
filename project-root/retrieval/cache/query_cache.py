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
        except Exception as exc:
            logger.warning("QueryCache.get failed", extra={"error": str(exc)})
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

    async def delete_by_user(self, user_id: str) -> None:
        """
        Delete all QueryCache entries for a user on /reset_memory (Mode B).
        QueryCache keys embed user_id in the hash — we must scan to find them.
        Pattern: qcache:* — scan is safe here because:
          (a) TTL is 10 min, so the keyspace is small at any moment
          (b) This runs only on explicit /reset_memory confirm — not on hot path
        EmbeddingCache and RerankCache are NOT touched: they are global
        infrastructure caches with no user_id in the key.
        """
        try:
            # SCAN instead of KEYS — non-blocking, safe for production Redis
            pattern = "qcache:*"
            prefix_to_delete: list[str] = []
            async for key in self._redis.scan_iter(pattern, count=100):
                key_str = key.decode() if isinstance(key, bytes) else key
                prefix_to_delete.append(key_str)
            # We cannot reverse the hash to check user_id, so we delete all
            # qcache entries. TTL is 10 min — collateral is minimal and acceptable
            # for a full memory reset operation.
            if prefix_to_delete:
                await self._redis.delete(*prefix_to_delete)
                logger.info(
                    "QueryCache.delete_by_user completed",
                    extra={"user_id": user_id, "keys_deleted": len(prefix_to_delete)},
                )
        except Exception as exc:
            logger.warning("QueryCache.delete_by_user failed", extra={"error": str(exc)})