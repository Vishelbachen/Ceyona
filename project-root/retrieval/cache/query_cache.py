from typing import Any, Dict, Optional
import time


class QueryCache:
    """
    AI Platform v4.7 — Query Cache

    RESPONSIBILITY:
    - Store retrieval results for identical queries
    - Reduce redundant retrieval computations
    - Provide deterministic key-value caching

    STRICT RULES:
    - No semantic similarity matching
    - No cache-based ranking decisions
    - No LLM / memory / reasoning usage
    - No orchestrator influence
    - No adaptive invalidation logic
    """

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}

    def _is_expired(self, timestamp: float) -> bool:
        """
        Checks if cached entry is expired.
        """

        return (time.time() - timestamp) > self.ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves cached value if not expired.
        """

        entry = self._store.get(key)

        if not entry:
            return None

        if self._is_expired(entry["timestamp"]):
            del self._store[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Stores value in cache.
        """

        self._store[key] = {
            "value": value,
            "timestamp": time.time(),
        }

    def invalidate(self, key: str) -> None:
        """
        Removes specific cache entry.
        """

        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """
        Clears entire cache.
        """

        self._store = {}