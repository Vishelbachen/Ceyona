from dataclasses import dataclass

from contracts.retrieval_contracts import RetrievedDocument


@dataclass(frozen=True)
class ContextRequest:
    documents: list[RetrievedDocument]
    max_chars: int = 3000
    separator: str = "\n\n---\n\n"


@dataclass(frozen=True)
class AssembledContext:
    text: str
    document_count: int
    truncated: bool = False