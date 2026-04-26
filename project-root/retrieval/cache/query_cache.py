from __future__ import annotations

from typing import Optional, List, Dict, Any
import hashlib
import json
import time


# =========================
# QUERY CACHE
# =========================
class QueryCache:
    """
    ROLE:
    - cache FINAL retrieval outputs
    - avoid recomputing full retrieval pipeline

    STRICT RULES:
    - NO embedding storage
    - NO ranking logic
    - NO semantic interpretation
    - ONLY raw result memoization
    """

    def __init__(self, ttl_seconds: int = 300):

        self._store: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    # =========================
    # KEY GENERATION
    # =========================
    def _key(self, query: str, top_k: int) -> str:

        normalized = f"{query.strip().lower()}::{top_k}"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    # =========================
    # GET CACHE
    # =========================
    def get(
        self,
        query: str,
        top_k: int,
    ) -> Optional[List[Dict[str, Any]]]:

        key = self._key(query, top_k)

        item = self._store.get(key)

        if not item:
            return None

        # TTL check
        if time.time() - item["ts"] > self._ttl:
            del self._store[key]
            return None

        return item["data"]

    # =========================
    # SET CACHE
    # =========================
    def set(
        self,
        query: str,
        top_k: int,
        results: List[Dict[str, Any]],
    ) -> None:

        key = self._key(query, top_k)

        self._store[key] = {
            "ts": time.time(),
            "data": results,
        }

    # =========================
    # INVALIDATION (OPTIONAL)
    # =========================
    def invalidate(self, query: str, top_k: int) -> None:

        key = self._key(query, top_k)

        if key in self._store:
            del self._store[key]

    # =========================
    # CLEAR ALL
    # =========================
    def clear(self) -> None:

        self._store.clear()

    # =========================
    # DEBUG ONLY
    # =========================
    def size(self) -> int:

        return len(self._store)