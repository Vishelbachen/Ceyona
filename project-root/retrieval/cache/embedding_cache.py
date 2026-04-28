from typing import Any, Dict, List, Optional
import time
import hashlib


class EmbeddingCache:
    """
    AI Platform v4.7 — Embedding Cache

    RESPONSIBILITY:
    - Cache query/document embeddings
    - Avoid recomputation of vectorization
    - Provide deterministic key → embedding storage

    STRICT RULES:
    - No semantic similarity search
    - No clustering or vector analysis
    - No LLM / memory / retrieval reasoning
    - No orchestrator influence
    - No adaptive caching logic
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}

    def _hash_key(self, text: str) -> str:
        """
        Creates deterministic cache key from text.
        """

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        """
        Checks expiration.
        """

        return (time.time() - timestamp) > self.ttl_seconds

    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieves cached embedding.
        """

        key = self._hash_key(text)
        entry = self._store.get(key)

        if not entry:
            return None

        if self._is_expired(entry["timestamp"]):
            del self._store[key]
            return None

        return entry["embedding"]

    def set(self, text: str, embedding: List[float]) -> None:
        """
        Stores embedding vector.
        """

        key = self._hash_key(text)

        self._store[key] = {
            "embedding": embedding,
            "timestamp": time.time(),
        }

    def invalidate(self, text: str) -> None:
        """
        Removes embedding from cache.
        """

        key = self._hash_key(text)

        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """
        Clears full cache.
        """

        self._store = {}