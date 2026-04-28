from typing import Any, Dict, List, Optional
import time
import hashlib


class RerankCache:
    """
    AI Platform v4.7 — Rerank Cache

    RESPONSIBILITY:
    - Cache reranked retrieval results
    - Avoid recomputing cross-encoder scoring
    - Provide deterministic query → ranked list mapping

    STRICT RULES:
    - No semantic reinterpretation of rankings
    - No adaptive caching or learning
    - No LLM / memory / retrieval reasoning
    - No influence on reranker logic
    - No orchestrator decisions
    """

    def __init__(self, ttl_seconds: int = 600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Dict[str, Any]] = {}

    def _hash_key(self, query: str, items: List[Dict[str, Any]]) -> str:
        """
        Creates deterministic cache key based on query + document ids.
        """

        doc_ids = ",".join([item.get("id", "") for item in items])
        raw_key = f"{query}:{doc_ids}"

        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        """
        Checks expiration.
        """

        return (time.time() - timestamp) > self.ttl_seconds

    def get(
        self,
        query: str,
        items: List[Dict[str, Any]],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves cached reranked result.
        """

        key = self._hash_key(query, items)
        entry = self._store.get(key)

        if not entry:
            return None

        if self._is_expired(entry["timestamp"]):
            del self._store[key]
            return None

        return entry["value"]

    def set(
        self,
        query: str,
        items: List[Dict[str, Any]],
        reranked: List[Dict[str, Any]],
    ) -> None:
        """
        Stores reranked results.
        """

        key = self._hash_key(query, items)

        self._store[key] = {
            "value": reranked,
            "timestamp": time.time(),
        }

    def invalidate(self, query: str, items: List[Dict[str, Any]]) -> None:
        """
        Removes cached rerank result.
        """

        key = self._hash_key(query, items)

        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        """
        Clears entire cache.
        """

        self._store = {}