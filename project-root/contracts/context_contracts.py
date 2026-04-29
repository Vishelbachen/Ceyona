from dataclasses import dataclass, field

from contracts.retrieval_contracts import RetrievalDocument


@dataclass(frozen=True)
class ContextRequest:
    documents: list[RetrievalDocument]
    max_chars: int = 3000
    separator: str = "\n\n---\n\n"


@dataclass(frozen=True)
class ContextResult:
    text: str
    documents_used: int
    truncated: bool = False