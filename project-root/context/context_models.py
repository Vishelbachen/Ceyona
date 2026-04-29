from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextChunk:
    content: str
    score: float
    source: str = ""


@dataclass(frozen=True)
class AssembledContext:
    chunks: list[ContextChunk]
    total_chars: int
    serialized: str