from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    user_id: str
    top_k: int = 5
    threshold: float = 0.7
    use_reranker: bool = True


@dataclass(frozen=True)
class RetrievedDocument:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    documents: list[RetrievedDocument]
    reranked: bool = False
    cached: bool = False