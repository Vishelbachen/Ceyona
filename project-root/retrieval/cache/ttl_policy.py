from typing import Dict, Optional


class TTLPolicy:
    """
    AI Platform v4.7 — TTL Policy

    RESPONSIBILITY:
    - Define static TTL rules for cache layers
    - Provide simple time-to-live values per cache type

    STRICT RULES:
    - No adaptive TTL adjustment
    - No usage-based optimization
    - No ML / LLM / memory / retrieval reasoning
    - No influence on system decisions
    """

    def __init__(
        self,
        default_ttl: int = 300,
        embedding_ttl: int = 3600,
        rerank_ttl: int = 600,
    ):
        self.default_ttl = default_ttl
        self.embedding_ttl = embedding_ttl
        self.rerank_ttl = rerank_ttl

    def get_ttl(self, cache_type: str) -> int:
        """
        Returns TTL based on cache type.
        """

        if cache_type == "embedding":
            return self.embedding_ttl

        if cache_type == "rerank":
            return self.rerank_ttl

        if cache_type == "query":
            return self.default_ttl

        return self.default_ttl

    def all(self) -> Dict[str, int]:
        """
        Returns all TTL configurations.
        """

        return {
            "default": self.default_ttl,
            "embedding": self.embedding_ttl,
            "rerank": self.rerank_ttl,
        }