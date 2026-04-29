from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    user_id: str
    top_k: int = 5
    use_reranker: bool = True
    use_cache: bool = True
    embedding_type: str = "large"   # "large" | "small"


@dataclass(frozen=True)
class RetrievalDocument:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    documents: list[RetrievalDocument]
    embedding_tokens: int = 0
    rerank_tokens: int = 0
    cache_hit: bool = False