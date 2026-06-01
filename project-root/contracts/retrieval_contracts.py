from dataclasses import dataclass, field
from enum import Enum


class RetrievalStatus(str, Enum):
    SUCCESS = "success"
    EMPTY = "empty"
    PROVIDER_ERROR = "provider_error"
    UNAVAILABLE = "unavailable"


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
    source_url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    documents: list[RetrievedDocument]
    embedding_tokens: int
    rerank_tokens: int
    cache_hit: bool = False
    reranked: bool = False   # True when cross-encoder reranking was applied
    cached: bool = False     # True when result came from cache