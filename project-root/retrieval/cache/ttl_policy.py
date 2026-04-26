from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CacheLevel = Literal["embedding", "query", "rerank"]


# =========================
# TTL POLICY CONFIG
# =========================
@dataclass(frozen=True)
class TTLPolicy:
    """
    ROLE:
    - define cache expiration rules
    - unify TTL behavior across retrieval cache layers

    STRICT RULES:
    - NO runtime logic
    - NO adaptive TTL
    - NO data access
    - ONLY static configuration
    """

    embedding_ttl: int = 3600       # 1 hour (vectors are stable)
    query_ttl: int = 300            # 5 minutes (pipeline results)
    rerank_ttl: int = 300           # 5 minutes (ML expensive step)


# =========================
# TTL RESOLVER
# =========================
class TTLPolicyResolver:
    """
    ROLE:
    - provide TTL values per cache layer
    - used by cache systems only

    STRICT RULES:
    - no decision making
    - no system state awareness
    """

    def __init__(self, policy: TTLPolicy = TTLPolicy()):
        self._policy = policy

    # =========================
    # GET TTL
    # =========================
    def get_ttl(self, level: CacheLevel) -> int:

        if level == "embedding":
            return self._policy.embedding_ttl

        if level == "query":
            return self._policy.query_ttl

        if level == "rerank":
            return self._policy.rerank_ttl

        # safe fallback (should never happen)
        return self._policy.query_ttl