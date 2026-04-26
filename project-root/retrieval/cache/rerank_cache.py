from __future__ import annotations

from typing import Optional, List, Dict, Any
import hashlib
import json
import time


# =========================
# RERANK CACHE
# =========================
class RerankCache:
    """
    ROLE:
    - cache FINAL reranked outputs (cross-encoder stage)
    - avoid recomputing expensive reranking

    STRICT RULES:
    - NO embeddings storage
    - NO retrieval logic
    - NO scoring modification
    - ONLY memoization of reranker output
    """

    def __init__(self, ttl_seconds: int = 300):

        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    # =========================
    # KEY GENERATION
    # =========================
    def _key(self, query: str, documents: List[Dict[str, Any]]) -> str:

        # deterministic representation of input set
        payload = {
            "q": query.strip().lower(),
            "docs": sorted([d["id"] for d in documents]),
        }

        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")

        return hashlib.sha256(encoded).hexdigest()

    # =========================
    # GET
    # =========================
    def get(
        self,
        query: str,
        documents: List[Dict[str, Any]],
    ) -> Optional[List[Dict[str, Any]]]:

        key = self._key(query, documents)

        item = self._store.get(key)

        if not item:
            return None

        # TTL validation
        if time.time() - item["ts"] > self._ttl:
            del self._store[key]
            return None

        return item["data"]

    # =========================
    # SET
    # =========================
    def set(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
    ) -> None:

        key = self._key(query, documents)

        self._store[key] = {
            "ts": time.time(),
            "data": results,
        }

    # =========================
    # INVALIDATION
    # =========================
    def invalidate(self, query: str, documents: List[Dict[str, Any]]) -> None:

        key = self._key(query, documents)

        if key in self._store:
            del self._store[key]

    # =========================
    # CLEAR CACHE
    # =========================
    def clear(self) -> None:

        self._store.clear()

    # =========================
    # DEBUG
    # =========================
    def size(self) -> int:

        return len(self._store)