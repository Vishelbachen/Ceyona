from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextChunk:
    content: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ContextBlock:
    chunks: list[ContextChunk]
    total_chars: int
    truncated: bool = False