from contracts.retrieval_contracts import RetrievalResult
from context.context_models import AssembledContext, ContextChunk

_MAX_CHARS = 3000
_MIN_SCORE = 0.5


def assemble(result: RetrievalResult) -> AssembledContext:
    """
    Convert retrieval result into context chunks.
    Deterministic assembly only. No ranking. No inference.
    """
    chunks: list[ContextChunk] = []
    total_chars = 0

    for doc in result.documents:
        if doc.score < _MIN_SCORE:
            continue
        if total_chars + len(doc.content) > _MAX_CHARS:
            break
        chunks.append(ContextChunk(
            content=doc.content,
            score=doc.score,
            source=doc.source,
        ))
        total_chars += len(doc.content)

    from context.serializer import serialize
    serialized = serialize(chunks)

    return AssembledContext(
        chunks=chunks,
        total_chars=total_chars,
        serialized=serialized,
    )