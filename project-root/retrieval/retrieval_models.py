from dataclasses import dataclass, field


@dataclass
class RankedCandidate:
    """A single document candidate with its reranking score."""
    content: str
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rerank_score: float = 0.0
    fused_score: float = 0.0
    source: str = "unknown"
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalStats:
    """Diagnostics returned alongside results — observability only."""
    dense_retrieved: int = 0
    sparse_retrieved: int = 0
    fused_count: int = 0
    reranked_count: int = 0
    cache_hit: bool = False
    embedding_tokens: int = 0
    rerank_tokens: int = 0