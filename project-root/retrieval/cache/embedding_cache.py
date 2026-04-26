from __future__ import annotations

from typing import Optional, Dict, Any
import hashlib
import numpy as np


# =========================
# EMBEDDING CACHE
# =========================
class EmbeddingCache:
    """
    ROLE:
    - cache embedding vectors for queries/texts
    - reduce embedding model calls

    STRICT RULES:
    - NO retrieval logic
    - NO ranking
    - NO semantic operations
    - ONLY key-value storage
    """

    def __init__(self):
        self._store: Dict[str, np.ndarray] = {}

    # =========================
    # KEY GENERATION
    # =========================
    def _key(self, text: str) -> str:

        normalized = text.strip().lower().encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    # =========================
    # GET
    # =========================
    def get(self, text: str) -> Optional[np.ndarray]:

        key = self._key(text)
        return self._store.get(key)

    # =========================
    # SET
    # =========================
    def set(self, text: str, vector: np.ndarray) -> None:

        key = self._key(text)
        self._store[key] = vector

    # =========================
    # CHECK
    # =========================
    def exists(self, text: str) -> bool:

        return self._key(text) in self._store

    # =========================
    # CLEAR (OPTIONAL MAINTENANCE)
    # =========================
    def clear(self) -> None:

        self._store.clear()

    # =========================
    # DEBUG ONLY
    # =========================
    def size(self) -> int:

        return len(self._store)