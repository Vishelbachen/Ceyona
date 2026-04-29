from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    user_id: str
    top_k: int = 10
    rerank_top_k: int = 3
    use_cache: bool = True
    embedding_type: str = "large"   # "large" | "small"


@dataclass(frozen=True)
class RetrievedDocument:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    documents: list[RetrievedDocument]
    embedding_tokens: int
    rerank_tokens: int
    cache_hit: bool = False