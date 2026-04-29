from dataclasses import dataclass


@dataclass(frozen=True)
class TTLPolicy:
    query_ttl_seconds: int = 300        # 5 min
    embedding_ttl_seconds: int = 3600   # 1 hour
    rerank_ttl_seconds: int = 600       # 10 min


ACTIVE_TTL = TTLPolicy()