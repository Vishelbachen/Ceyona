from __future__ import annotations

from typing import List, Dict, Any, Optional
import math


# =========================
# VECTOR MEMORY
# =========================
class VectorMemory:
    """
    ROLE:
    - store embeddings (vectors)
    - perform similarity search

    STRICT RULES:
    - no business logic
    - no semantic interpretation
    - no embedding generation
    - no ranking strategies beyond similarity
    """

    def __init__(self):
        self._store: List[Dict[str, Any]] = []

    # =========================
    # ADD VECTOR
    # =========================
    def add(
        self,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> None:

        if not vector:
            return

        self._store.append({
            "vector": vector,
            "payload": payload,
        })

    # =========================
    # SEARCH (COSINE SIMILARITY)
    # =========================
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:

        if not query_vector or not self._store:
            return []

        results = []

        for item in self._store:
            sim = self._cosine_similarity(query_vector, item["vector"])

            results.append({
                "score": sim,
                "payload": item["payload"],
            })

        # sort by similarity (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    # =========================
    # CLEAR MEMORY (OPTIONAL)
    # =========================
    def clear(self) -> None:
        self._store.clear()

    # =========================
    # INTERNAL: COSINE SIMILARITY
    # =========================
    def _cosine_similarity(
        self,
        v1: List[float],
        v2: List[float],
    ) -> float:

        if len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return dot / (norm1 * norm2)