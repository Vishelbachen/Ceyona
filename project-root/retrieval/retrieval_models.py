from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryVector:
    text: str
    embedding: list[float]
    model: str


@dataclass(frozen=True)
class ScoredCandidate:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)